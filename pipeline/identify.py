"""
Sruthi — Stage 1: ShazamIO audio fingerprint identification
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Walks a source path for MP3 files, fingerprints each one via ShazamIO, and
writes the result to music.db. Files are deduplicated by MD5 hash — re-running
on the same file is a no-op unless it previously errored. Language is inferred
from the containing folder name (e.g. Input/Tamil/ → language='Tamil').

Identification sources set by this module:
  id_source='shazam'          — matched by ShazamIO fingerprint
  id_source='collection-fix'  — Shazam failed but filename contained a
                                 "from <Album>" clue (see collection.py, issue #4)

Files shorter than 8 seconds cannot be fingerprinted reliably and are
immediately set to no_match with an explanatory error_msg.

Docs:
  How ShazamIO fingerprinting works — DOCS/MUSIC_FILES_PRIMER.md
  Design rationale for ShazamIO     — DOCS/DESIGN_DECISIONS.md
  Stage 1 in the pipeline overview  — DOCS/ARCHITECTURE.md
"""

import asyncio
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import error as ID3Error
from shazamio import Shazam

from pipeline import config
from pipeline.collection import extract_collection_clue
from pipeline.db import (
    get_connection,
    increment_duplicate_count,
    insert_song,
    song_exists_by_hash,
    update_song,
)
from pipeline.runner import GREEN, YELLOW, RED, RESET


def compute_md5(file_path: str) -> str:
    """Return the MD5 hex digest of a file. Used as the deduplication key in music.db."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def detect_language(file_path: str) -> str:
    """
    Infer language from the containing folder name by walking up the path.
    Matches case-insensitively against config.LANGUAGES.
    Returns 'Other' if no match found. See issue #25 for song-level detection plans.
    """
    path = Path(os.path.abspath(file_path))
    languages_lower = {lang.lower(): lang for lang in config.LANGUAGES}
    for parent in path.parents:
        if parent.name.lower() in languages_lower:
            return languages_lower[parent.name.lower()]
    return "Other"


def walk_mp3s(source_path: str) -> list[str]:
    """
    Recursively collect all MP3 files under source_path.
    Accepts a single file path or a directory. Returns sorted absolute paths.
    Only extensions in config.SUPPORTED_EXTENSIONS are included.
    """
    results = []
    source = Path(os.path.abspath(source_path))
    if source.is_file():
        if source.suffix.lower() in config.SUPPORTED_EXTENSIONS:
            results.append(str(source))
    else:
        for root, _, files in os.walk(source):
            for fname in files:
                if Path(fname).suffix.lower() in config.SUPPORTED_EXTENSIONS:
                    results.append(str(Path(root) / fname))
    return sorted(results)


def parse_shazam_response(out: dict) -> dict | None:
    """
    Parse a raw ShazamIO response using the exact field paths documented in
    the README 'ShazamIO response parsing reference' section.
    Returns None if no track was identified.
    """
    track = out.get("track")
    if not track:
        return None

    title = track.get("title", "")
    artist = track.get("subtitle", "")
    genre = track.get("genres", {}).get("primary", "")
    cover_url = track.get("images", {}).get("coverart", "")

    album = ""
    year = ""
    for section in track.get("sections", []):
        if section.get("type") == "SONG":
            for item in section.get("metadata", []):
                if item.get("title") == "Album":
                    album = item.get("text", "")
                elif item.get("title") == "Released":
                    year = item.get("text", "")
            break

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "year": year,
        "genre": genre,
        "cover_url": cover_url,
    }


def _get_song_by_id(song_id: str) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM songs WHERE song_id = ?", (song_id,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


async def identify_file(file_path: str, run_id: str, shazam: Shazam) -> dict:
    """
    Full Stage 1 pipeline for one file. Returns {} if the file was skipped
    (already in DB). Returns the updated song row dict otherwise.
    """
    # 1. Dedup check — same file already in DB
    file_hash = compute_md5(file_path)
    song_id = None

    if song_exists_by_hash(file_hash):
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT song_id, file_path, status FROM songs WHERE file_hash = ?",
                (file_hash,)
            ).fetchone()
            if row:
                if row["status"] in ("error", "pending", "removed"):
                    # Error and pending files are retried — reuse existing song_id
                    song_id = row["song_id"]
                    update_song(song_id, status="pending", error_msg=None, file_path=file_path)
                elif row["file_path"] != file_path and row["status"] != "done":
                    # File was renamed — update stored path so passes can find it
                    update_song(row["song_id"], file_path=file_path)
                    print(f"[PATH]  path updated for {row['song_id']}: {file_path}")
                    return {}
                else:
                    # Already processed — skip
                    if row["status"] == "done":
                        increment_duplicate_count(row["song_id"])
                    print(f"[SKIP]  already in DB: {file_path}")
                    return {}
            else:
                return {}
        finally:
            conn.close()

    if song_id is None:
        # 2. Language
        language = detect_language(file_path)
        # 3. Insert as pending
        song_id = insert_song(file_path, file_hash, language, run_id)

    # 3b. Short-file guard — files under 8s cannot be reliably fingerprinted
    try:
        audio = MP3(file_path)
        duration = audio.info.length
    except (HeaderNotFoundError, ID3Error):
        duration = 999  # not a valid MP3 — let Shazam attempt it and fail gracefully

    if duration < 8.0:
        update_song(song_id, status="no_match",
                    error_msg=f"too short for fingerprinting ({duration:.1f}s)")
        return _get_song_by_id(song_id)

    # 4 & 5. Shazam call + parse
    try:
        out = await shazam.recognize(file_path)
        result = parse_shazam_response(out)

        now = datetime.now(timezone.utc).isoformat()
        if result is not None:
            update_song(
                song_id,
                status="identified",
                shazam_title=result["title"],
                shazam_artist=result["artist"],
                shazam_album=result["album"],
                shazam_year=result["year"],
                shazam_genre=result["genre"],
                shazam_cover_url=result["cover_url"],
                # seed final_* with shazam_* so later stages have defaults
                final_title=result["title"],
                final_artist=result["artist"],
                final_album=result["album"],
                final_year=result["year"],
                final_genre=result["genre"],
                id_source="shazam",
                last_attempt_at=now,
                run_id=run_id,
            )
        else:
            # Shazam failed — try extracting album clues from the filename
            clue = extract_collection_clue(file_path)
            if clue:
                update_song(
                    song_id,
                    status="identified",
                    final_title=clue["title"],
                    final_album=clue["album"],
                    id_source="collection-fix",
                    last_attempt_at=now,
                    run_id=run_id,
                )
            else:
                update_song(song_id, status="no_match", last_attempt_at=now, run_id=run_id)

    except Exception as e:
        update_song(song_id, status="error", error_msg=str(e), run_id=run_id)

    return _get_song_by_id(song_id)


def run_identification(source_path: str, run_id: str) -> dict:
    """
    Walk source_path for MP3s and run Stage 1 identification on each.
    Returns summary dict: {total, identified, no_match, errors, skipped}.
    """
    mp3s = walk_mp3s(source_path)
    total = len(mp3s)
    counts = {"total": total, "identified": 0, "no_match": 0, "errors": 0, "skipped": 0}

    async def _run():
        shazam = Shazam()
        for i, fp in enumerate(mp3s, 1):
            name = Path(fp).name
            song = await identify_file(fp, run_id, shazam)

            if not song:
                # empty dict → skipped (already in DB)
                print(f"[--------] ↷ skipped     ({i}/{total}) {name}")
                counts["skipped"] += 1
            else:
                status = song.get("status", "")
                song_id = song.get("song_id", "--------")
                lang = song.get("language", "")

                if status == "identified":
                    if song.get("id_source") == "collection-fix":
                        title = song.get("final_title", "")
                        album = song.get("final_album", "")
                        print(f"{GREEN}[{song_id}] ✓ collection  ({i}/{total}) {lang} | {title} (from {album}){RESET}")
                    else:
                        title = song.get("shazam_title", "")
                        artist = song.get("shazam_artist", "")
                        print(f"{GREEN}[{song_id}] ✓ identified  ({i}/{total}) {lang} | {title} — {artist}{RESET}")
                    counts["identified"] += 1
                elif status == "no_match":
                    err = song.get("error_msg") or ""
                    if "too short" in err:
                        print(f"{YELLOW}[{song_id}] ⚠ too short   ({i}/{total}) {lang} | {name} — {err}{RESET}")
                    else:
                        print(f"{YELLOW}[{song_id}] ✗ no match    ({i}/{total}) {lang} | {name}{RESET}")
                    counts["no_match"] += 1
                elif status == "error":
                    err = song.get("error_msg", "")
                    print(f"{RED}[{song_id}] ! error       ({i}/{total}) {lang} | {name} — {err}{RESET}")
                    counts["errors"] += 1

            if song and i < total:
                await asyncio.sleep(config.SHAZAM_SLEEP_SEC)

    asyncio.run(_run())
    return counts
