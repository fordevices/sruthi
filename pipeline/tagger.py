"""
Stage 3 — Mutagen ID3 tag writer.
Field priority and ID3 patterns follow the README "Mutagen ID3 tagging reference" section.
"""

import json
import requests
from mutagen.id3 import (
    APIC,
    ID3,
    ID3NoHeaderError,
    TALB,
    TDRC,
    TCON,
    TIT2,
    TPE1,
    TXXX,
)

from pipeline.db import get_songs_by_status, update_song
from pipeline.runner import GREEN, RED, RESET


# ---------------------------------------------------------------------------
# Field priority rule (README: Mutagen ID3 tagging reference)
# ---------------------------------------------------------------------------

def resolve(final_val, shazam_val, fallback: str = "") -> str:
    """
    final_* wins if non-empty after strip.
    shazam_* is second choice if non-empty after strip.
    fallback (default "") is last resort.
    """
    if final_val and str(final_val).strip():
        return str(final_val).strip()
    if shazam_val and str(shazam_val).strip():
        return str(shazam_val).strip()
    return fallback


def _source_label(final_val, shazam_val) -> str:
    """Return display label showing which source won, for dry-run output."""
    if final_val and str(final_val).strip():
        return "[final_*]"
    if shazam_val and str(shazam_val).strip():
        return "[shazam_*]"
    return "[empty]"


# ---------------------------------------------------------------------------
# Core tagging logic
# ---------------------------------------------------------------------------

def tag_file(song: dict, dry_run: bool = False) -> bool:
    """
    Write ID3 tags for one identified song.
    Returns True on success (or dry_run), False on write error.
    """
    song_id   = song["song_id"]
    file_path = song["file_path"]

    # Resolve all fields per priority rule
    title  = resolve(song.get("final_title"),  song.get("shazam_title"))
    artist = resolve(song.get("final_artist"), song.get("shazam_artist"))
    album  = resolve(song.get("final_album"),  song.get("shazam_album"))
    year   = resolve(song.get("final_year"),   song.get("shazam_year"))
    genre  = resolve(song.get("final_genre"),  song.get("shazam_genre"))
    cover  = song.get("shazam_cover_url") or ""

    if dry_run:
        def label(key):
            return _source_label(song.get(f"final_{key}"), song.get(f"shazam_{key}"))

        print(f"  [{song_id}] DRY RUN: {file_path}")
        print(f"    TIT2  title  : {title!r:<50} {label('title')}")
        print(f"    TPE1  artist : {artist!r:<50} {label('artist')}")
        print(f"    TALB  album  : {album!r:<50} {label('album')}")
        print(f"    TDRC  year   : {year!r:<50} {label('year')}")
        print(f"    TCON  genre  : {genre!r:<50} {label('genre')}")
        print(f"    TXXX  id     : {song_id!r:<50} [always]")
        cover_label = f"{cover[:60]}..." if len(cover) > 60 else cover
        print(f"    APIC  cover  : {'(download)' if cover else '(skip — no URL)':<50} {'[shazam_cover_url]' if cover else '[empty]'}")
        print()
        return True

    try:
        try:
            tags = ID3(file_path)
        except ID3NoHeaderError:
            tags = ID3()

        # Snapshot existing tags before overwriting
        meta_before = json.dumps({
            "title":  str(tags.get("TIT2", "")),
            "artist": str(tags.get("TPE1", "")),
            "album":  str(tags.get("TALB", "")),
            "year":   str(tags.get("TDRC", "")),
            "genre":  str(tags.get("TCON", "")),
        })

        # Always write title and artist (required for any useful tag)
        if title:
            tags["TIT2"] = TIT2(encoding=3, text=title)
        if artist:
            tags["TPE1"] = TPE1(encoding=3, text=artist)

        # Omit optional frames if empty (per tagging reference)
        if album:
            tags["TALB"] = TALB(encoding=3, text=album)
        if year:
            tags["TDRC"] = TDRC(encoding=3, text=year)
        if genre:
            tags["TCON"] = TCON(encoding=3, text=genre)

        # Always write pipeline tracking tag
        tags["TXXX:PIPELINE_ID"] = TXXX(encoding=3, desc="PIPELINE_ID", text=song_id)

        # Cover art — non-fatal on failure
        if cover:
            try:
                resp = requests.get(cover, timeout=10)
                resp.raise_for_status()
                tags["APIC:Cover"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=resp.content,
                )
            except Exception as cover_err:
                print(f"  [{song_id}] cover art skipped: {cover_err}")

        tags.save(file_path)
        meta_after = json.dumps({
            "title": title, "artist": artist, "album": album,
            "year": year, "genre": genre,
        })
        update_song(song_id, status="tagged", meta_before=meta_before, meta_after=meta_after)
        return True

    except Exception as e:
        update_song(song_id, status="error", error_msg=str(e))
        return False


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run_tagging(dry_run: bool = False) -> dict:
    """
    Tag all songs with status="identified".
    Returns {tagged, errors, skipped}.
    """
    songs = get_songs_by_status("identified")
    tagged = errors = skipped = 0

    if not songs:
        print("No identified songs to tag.")
        return {"tagged": 0, "errors": 0, "skipped": 0}

    if dry_run:
        print(f"DRY RUN — would tag {len(songs)} song(s):\n")

    for song in songs:
        song_id = song["song_id"]
        title   = resolve(song.get("final_title"),  song.get("shazam_title"))
        artist  = resolve(song.get("final_artist"), song.get("shazam_artist"))
        override = song.get("override_used")
        year_src = _source_label(song.get("final_year"), song.get("shazam_year"))
        year_val = resolve(song.get("final_year"), song.get("shazam_year"))

        ok = tag_file(song, dry_run=dry_run)

        if dry_run:
            # dry_run detail already printed inside tag_file; just count
            tagged += 1
            continue

        if ok:
            tagged += 1
            suffix = ""
            if override:
                suffix = "  (override)"
            elif year_src == "[final_*]" and song.get("final_year") != song.get("shazam_year"):
                suffix = f"  (year: {year_val} from final_*)"
            print(f"{GREEN}[{song_id}] ✓ tagged   {title} — {artist}{suffix}{RESET}")
        else:
            errors += 1
            err = song.get("error_msg", "unknown error")
            name = song.get("file_path", "").split("/")[-1]
            print(f"{RED}[{song_id}] ✗ error    {name} — {err}{RESET}")

    print()
    if dry_run:
        print(f"Dry run complete — {tagged} song(s) previewed, nothing written.")
    else:
        print(f"Tagging complete — {tagged} tagged, {errors} errors, {skipped} skipped.")

    return {"tagged": tagged, "errors": errors, "skipped": skipped}
