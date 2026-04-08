"""
Sruthi — metadata search pass (--metadata-search)
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Third identification pass for songs that Shazam and AcoustID both failed on.
Builds the best available text query from existing ID3 tags (TIT2 + TPE1 preferred
over cleaned filename), searches iTunes, and presents up to 3 candidates for manual
selection. No API key required.

Query priority: existing ID3 tags (TIT2 + TPE1) > cleaned filename stem.
Sets id_source='metadata-search' on acceptance.

iTunes Search API: no rate limit documented; 5-result limit applied client-side.

Docs:
  Metadata search pass walkthrough — DOCS/USER_GUIDE.md  (Metadata search pass)
Issues:
  #3  — original metadata search implementation
  #13 — iTunes added as second source; ID3 tag priority over filename
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from mutagen.id3 import ID3, ID3NoHeaderError

from pipeline.db import get_all_songs, get_songs_by_status, update_song
from pipeline.review import parse_override, play_file
from pipeline.runner import GREEN, YELLOW, RED, RESET

_DIVIDER = "─" * 44
_ITUNES_URL = "https://itunes.apple.com/search"


# ---------------------------------------------------------------------------
# Filename cleaning
# ---------------------------------------------------------------------------

# Patterns to strip before searching (track numbers, common junk)
_STRIP_PATTERNS = [
    re.compile(r'^track\d+[\s._\-]+', re.IGNORECASE),  # "track03 ", "track03-"
    re.compile(r'^\d{1,3}[\s._\-]+'),                  # leading track number: "01 ", "01-"
    re.compile(r'\(\s*\d{4}\s*\)'),                    # year in parens: (2001)
    re.compile(r'\[.*?\]'),                            # anything in square brackets
    re.compile(r'_+'),                                 # underscores → spaces (applied last)
]


def clean_filename(file_path: str) -> str:
    """
    Strip extension and common noise from a filename to produce a search term.
    E.g. '01_vaseegara_minnale_[320kbps].mp3' → 'vaseegara minnale'
    """
    stem = Path(file_path).stem
    for pattern in _STRIP_PATTERNS[:-1]:   # all but underscore replacement
        stem = pattern.sub(' ', stem)
    stem = _STRIP_PATTERNS[-1].sub(' ', stem)   # underscores → spaces
    return stem.strip(' -.')


def _get_query(song: dict, file_path: str) -> str:
    """
    Build the best available search query for a song.
    Priority: existing ID3 tags (TIT2 + TPE1) > cleaned filename.
    """
    try:
        tags = ID3(file_path)
        title = str(tags.get("TIT2", "")).strip()
        artist = str(tags.get("TPE1", "")).strip()
        if title and artist:
            return f"{title} {artist}"
        if title:
            return title
        if artist:
            return artist
    except (ID3NoHeaderError, Exception):
        pass
    return clean_filename(file_path)


# ---------------------------------------------------------------------------
# iTunes search
# ---------------------------------------------------------------------------

def _search_itunes(query: str) -> list[dict]:
    """
    Search iTunes for the given query string.
    Returns up to 3 matches as dicts: {source, score, title, artist, album, year}.
    Returns [] on any error.
    """
    try:
        resp = requests.get(
            _ITUNES_URL,
            params={"term": query, "entity": "song", "limit": 5},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  iTunes search error: {e}")
        return []

    matches = []
    for item in data.get("results", []):
        title = item.get("trackName", "")
        artist = item.get("artistName", "")
        album = item.get("collectionName", "")
        release_date = item.get("releaseDate", "")
        year = release_date[:4] if release_date else ""

        if title:
            matches.append({
                "source": "iTunes",
                "score": None,
                "title": title,
                "artist": artist,
                "album": album,
                "year": year,
            })

    return matches[:3]


# ---------------------------------------------------------------------------
# Interactive review
# ---------------------------------------------------------------------------

def _print_candidates(song: dict, query: str, matches: list[dict]) -> None:
    print(_DIVIDER)
    print(f"Song ID  : {song['song_id']}")
    print(f"File     : {song['file_path']}")
    print(f"Language : {song.get('language', '')}")
    print(f"Status   : {song.get('status', '')}")
    print(f"Search   : {query!r}")
    print(f"── Candidates ──")
    for i, m in enumerate(matches, 1):
        score_str = f"{m['score']:>3}%" if m["score"] is not None else "    "
        print(f"  [{i}] {score_str}  [{m['source']:<6}]  {m['title']} — {m['artist']}"
              f"  |  {m['album'] or '(no album)'}  {m['year'] or ''}")
    print(_DIVIDER)


def _review_candidates(song: dict, query: str, matches: list[dict]) -> str:
    """
    Let user pick a candidate, edit, play, skip, or quit.
    Returns: "accepted" | "edited" | "skipped" | "quit"
    """
    song_id = song["song_id"]
    now = datetime.now(timezone.utc).isoformat()
    _print_candidates(song, query, matches)

    options = "/".join(str(i) for i in range(1, len(matches) + 1))
    while True:
        print(f"[{options}] Pick  [e] Edit manually  [p] Play  [s] Skip  [q] Quit")
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

        # Number pick
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            match = matches[int(choice) - 1]
            update_song(
                song_id,
                status="identified",
                final_title=match["title"],
                final_artist=match["artist"],
                final_album=match["album"],
                final_year=match["year"],
                id_source="metadata-search",
                last_attempt_at=now,
            )
            print(f"{GREEN}✓ Accepted [{choice}]. Status → identified.{RESET}\n")
            return "accepted"

        elif choice == "p":
            play_file(song["file_path"])
            _print_candidates(song, query, matches)

        elif choice == "e":
            print("Enter: Title | Artist | Album | Year")
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            if not raw:
                print("No changes.")
                continue

            parsed = parse_override(raw)
            print("Will save:")
            for k in ("title", "artist", "album", "year"):
                print(f"  {k.capitalize():<6} : {parsed[k] or '(empty)'}")
            try:
                confirm = input("Confirm? [y/n] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            if confirm == "y":
                update_song(
                    song_id,
                    status="identified",
                    final_title=parsed["title"],
                    final_artist=parsed["artist"],
                    final_album=parsed["album"],
                    final_year=parsed["year"],
                    id_source="metadata-search",
                    last_attempt_at=now,
                    override_used=1,
                    override_raw=raw,
                )
                print(f"{GREEN}✓ Saved. Status → identified.{RESET}\n")
                return "edited"

        elif choice == "s":
            update_song(song_id, last_attempt_at=now)
            print()
            return "skipped"

        elif choice == "q":
            return "quit"

        else:
            print("Invalid choice.")


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run_filename_pass(folder: str = None, all_songs: bool = False) -> dict:
    """
    Process songs by searching iTunes with their best available query (ID3 tags
    preferred over cleaned filename) and presenting candidates for manual verification.

    folder    — if set, only process songs whose file_path contains this string
    all_songs — if True, process all songs regardless of status;
                otherwise only no_match songs

    Returns {processed, accepted, skipped, no_match, errors}.
    """
    if all_songs:
        songs = get_all_songs()
    else:
        songs = get_songs_by_status("no_match")

    if folder:
        songs = [s for s in songs if folder in s["file_path"]]

    total = len(songs)

    if total == 0:
        print("No songs to process with metadata search.")
        return {"processed": 0, "accepted": 0, "skipped": 0,
                "no_match": 0, "errors": 0}

    scope = "all songs" if all_songs else "no_match songs"
    folder_note = f" in '{folder}'" if folder else ""
    print(f"Metadata search — {total} {scope}{folder_note}")
    print("[1…6] Pick candidate  [e]dit  [p]lay  [s]kip  [q]uit\n")

    processed = accepted = skipped = no_match = errors = 0

    for i, song in enumerate(songs, 1):
        song_id = song["song_id"]

        if not os.path.exists(song["file_path"]):
            print(f"{YELLOW}[{song_id}] File no longer exists — skipping{RESET}\n")
            processed += 1
            continue

        query = _get_query(song, song["file_path"])
        print(f"({i}/{total}) Searching: {query!r}")

        if not query:
            print(f"{YELLOW}[{song_id}] No usable query — skipped{RESET}\n")
            no_match += 1
            processed += 1
            continue

        matches = _search_itunes(query)

        if not matches:
            print(f"{YELLOW}[{song_id}] No matches found — stays {song['status']}{RESET}\n")
            no_match += 1
            processed += 1
        else:
            result = _review_candidates(song, query, matches)
            processed += 1

            if result in ("accepted", "edited"):
                accepted += 1
            elif result == "skipped":
                skipped += 1
            elif result == "quit":
                break

    print(
        f"Metadata search complete — {accepted} accepted, {skipped} skipped, "
        f"{no_match} no match, {errors} errors."
    )
    return {
        "processed": processed,
        "accepted": accepted,
        "skipped": skipped,
        "no_match": no_match,
        "errors": errors,
    }
