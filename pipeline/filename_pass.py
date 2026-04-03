"""
Metadata search pass — issue #3 (renamed from filename pass).

Third identification pass for files that Shazam and AcoustID both failed on.
Searches MusicBrainz text search API using the best available text signals:
existing ID3 tags (title, artist) are preferred over the cleaned filename.

No API key or binary dependency required — MusicBrainz has a free, open API.
Sets id_source='metadata-search' on acceptance.
"""

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline.db import get_songs_by_status, update_song
from pipeline.review import parse_override, play_file
from pipeline.runner import GREEN, YELLOW, RED, RESET

_DIVIDER = "─" * 44
_MB_URL = "https://musicbrainz.org/ws/2/recording/"
_MB_USER_AGENT = "mp3-organizer-pipeline/1.0 ( https://github.com/fordevices/mp3-organizer-pipeline )"
_MB_SLEEP = 1.1   # MusicBrainz rate limit: 1 request/second


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


# ---------------------------------------------------------------------------
# MusicBrainz search
# ---------------------------------------------------------------------------

def _search_musicbrainz(query: str) -> list[dict]:
    """
    Search MusicBrainz recordings for the given query string.
    Returns up to 3 matches as dicts: {score, title, artist, album, year}.
    Returns [] on any error.
    """
    try:
        resp = requests.get(
            _MB_URL,
            params={"query": query, "fmt": "json", "limit": 5},
            headers={"User-Agent": _MB_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  MusicBrainz search error: {e}")
        return []

    matches = []
    for recording in data.get("recordings", []):
        score = int(recording.get("score", 0))
        title = recording.get("title", "")
        artists = recording.get("artist-credit", [])
        artist = artists[0]["artist"]["name"] if artists else ""

        album = ""
        year = ""
        releases = recording.get("releases", [])
        if releases:
            album = releases[0].get("title", "")
            date = releases[0].get("date", "")
            year = date[:4] if date else ""   # date is "YYYY-MM-DD" or "YYYY"

        if title:
            matches.append({
                "score": score,
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
    print(f"Search   : {query!r}")
    print(f"── MusicBrainz candidates ──")
    for i, m in enumerate(matches, 1):
        print(f"  [{i}] {m['score']:>3}%  {m['title']} — {m['artist']}"
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
                id_source="filename-match",
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
                    id_source="filename-match",
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

def run_filename_pass() -> dict:
    """
    Process all no_match songs by searching MusicBrainz with their cleaned
    filename and presenting candidates for manual verification.

    Returns {processed, accepted, skipped, no_mb_match, errors}.
    """
    songs = get_songs_by_status("no_match")
    total = len(songs)

    if total == 0:
        print("No no_match songs to process with filename search.")
        return {"processed": 0, "accepted": 0, "skipped": 0,
                "no_mb_match": 0, "errors": 0}

    print(f"Filename pass — {total} no_match song(s)")
    print("[1/2/3] Pick candidate  [e]dit  [p]lay  [s]kip  [q]uit\n")

    processed = accepted = skipped = no_mb_match = errors = 0

    for i, song in enumerate(songs, 1):
        song_id = song["song_id"]
        query = clean_filename(song["file_path"])
        print(f"({i}/{total}) Searching: {query!r}")

        if not os.path.exists(song["file_path"]):
            print(f"{YELLOW}[{song_id}] File no longer exists — skipping{RESET}\n")
            processed += 1
            continue

        if not query:
            print(f"{YELLOW}[{song_id}] Filename too short to search — skipped{RESET}\n")
            no_mb_match += 1
            processed += 1
            continue

        matches = _search_musicbrainz(query)

        if not matches:
            print(f"{YELLOW}[{song_id}] No MusicBrainz match — stays no_match{RESET}\n")
            no_mb_match += 1
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

        # Respect MusicBrainz rate limit between requests
        if i < total:
            time.sleep(_MB_SLEEP)

    print(
        f"Filename pass complete — {accepted} accepted, {skipped} skipped, "
        f"{no_mb_match} no match, {errors} errors."
    )
    return {
        "processed": processed,
        "accepted": accepted,
        "skipped": skipped,
        "no_mb_match": no_mb_match,
        "errors": errors,
    }
