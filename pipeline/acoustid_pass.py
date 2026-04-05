"""
Sruthi — AcoustID fallback identification pass (--acoustid)
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Second audio fingerprinting pass for songs that ShazamIO could not identify.
Uses the open AcoustID + MusicBrainz database via the Chromaprint fpcalc binary.
Presents the best candidate to the user for verification before saving.

Flow per song:
  1. Fingerprint with fpcalc (Chromaprint)
  2. Query AcoustID API — returns candidate recordings from MusicBrainz
  3. Present best match with confidence score for user verification
  4. On acceptance: status='identified', id_source='acoustid'

Prerequisites (see DOCS/USER_GUIDE.md — AcoustID fallback pass):
  - fpcalc binary: brew install chromaprint / apt install libchromaprint-tools
  - ACOUSTID_API_KEY env var — free registration at https://acoustid.org
  - pip install pyacoustid

This is the recommended fallback if ShazamIO ever becomes unavailable.
See DOCS/DESIGN_DECISIONS.md for the full rationale and comparison table.

Docs:
  AcoustID setup and usage  — DOCS/USER_GUIDE.md  (AcoustID fallback pass)
  Why ShazamIO was chosen    — DOCS/DESIGN_DECISIONS.md
Issues:
  #2 — AcoustID pass implementation
"""

import shutil
import os
from datetime import datetime, timezone

from pipeline import config
from pipeline.db import get_songs_by_status, update_song
from pipeline.review import parse_override, play_file
from pipeline.runner import GREEN, YELLOW, RED, RESET

_DIVIDER = "─" * 44


# ---------------------------------------------------------------------------
# Prerequisites check
# ---------------------------------------------------------------------------

def _check_prerequisites() -> None:
    """Raise RuntimeError if fpcalc or the API key are missing."""
    if not shutil.which("fpcalc"):
        raise RuntimeError(
            "fpcalc not found. Install Chromaprint:\n"
            "  macOS:  brew install chromaprint\n"
            "  Linux:  sudo apt install libchromaprint-tools\n"
            "  Windows: download fpcalc from https://acoustid.org/chromaprint"
        )
    if not config.ACOUSTID_API_KEY:
        raise RuntimeError(
            "ACOUSTID_API_KEY not set.\n"
            "Register free at https://acoustid.org then:\n"
            "  export ACOUSTID_API_KEY=your_key_here"
        )


# ---------------------------------------------------------------------------
# Fingerprint + AcoustID lookup
# ---------------------------------------------------------------------------

def _lookup(file_path: str) -> list[dict]:
    """
    Fingerprint file and query AcoustID.
    Returns list of match dicts sorted by score descending.
    Each dict: {score, title, artist, album, year}.
    Returns [] if no matches or on any error.
    """
    import acoustid

    try:
        duration, fingerprint = acoustid.fingerprint_file(file_path)
    except Exception as e:
        print(f"  Fingerprint error: {e}")
        return []

    try:
        response = acoustid.lookup(
            config.ACOUSTID_API_KEY,
            fingerprint,
            duration,
            meta="recordings releases releasegroups tracks",
        )
    except Exception as e:
        print(f"  AcoustID lookup error: {e}")
        return []

    matches = []
    for result in response.get("results", []):
        score = result.get("score", 0)
        for recording in result.get("recordings", []):
            title = recording.get("title", "")
            artists = recording.get("artists", [])
            artist = artists[0]["name"] if artists else ""

            album = ""
            year = ""
            releases = recording.get("releases", [])
            if releases:
                album = releases[0].get("title", "")
                date = releases[0].get("date", {})
                if date:
                    raw_year = date.get("year", "")
                    year = str(raw_year) if raw_year else ""

            if title:
                matches.append({
                    "score": score,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "year": year,
                })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


# ---------------------------------------------------------------------------
# Interactive review
# ---------------------------------------------------------------------------

def _print_match(song: dict, match: dict) -> None:
    score_pct = f"{match['score']:.0%}"
    print(_DIVIDER)
    print(f"Song ID  : {song['song_id']}")
    print(f"File     : {song['file_path']}")
    print(f"Language : {song.get('language', '')}")
    print(f"── AcoustID match  (confidence: {score_pct}) ──")
    print(f"Title    : {match['title'] or '(none)'}")
    print(f"Artist   : {match['artist'] or '(none)'}")
    print(f"Album    : {match['album'] or '(none)'}")
    print(f"Year     : {match['year'] or '(none)'}")
    print(_DIVIDER)


def _review_match(song: dict, match: dict) -> str:
    """
    Present proposed AcoustID match and get user decision.
    Returns: "accepted" | "edited" | "skipped" | "quit"
    """
    song_id = song["song_id"]
    now = datetime.now(timezone.utc).isoformat()
    _print_match(song, match)

    while True:
        print("[a] Accept  [e] Edit  [p] Play  [s] Skip  [q] Quit")
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

        if choice == "a":
            update_song(
                song_id,
                status="identified",
                final_title=match["title"],
                final_artist=match["artist"],
                final_album=match["album"],
                final_year=match["year"],
                id_source="acoustid",
                last_attempt_at=now,
            )
            print(f"{GREEN}✓ Accepted. Status → identified.{RESET}\n")
            return "accepted"

        elif choice == "p":
            play_file(song["file_path"])
            _print_match(song, match)

        elif choice == "e":
            print("Current proposal:")
            for k in ("title", "artist", "album", "year"):
                print(f"  {k.capitalize():<6} : {match[k] or '(none)'}")
            print("Enter: Title | Artist | Album | Year  (blank field = keep proposal)")
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            parsed = parse_override(raw)
            merged = {k: parsed[k] or match[k] for k in ("title", "artist", "album", "year")}

            print("Will save:")
            for k, v in merged.items():
                print(f"  {k.capitalize():<6} : {v or '(empty)'}")
            try:
                confirm = input("Confirm? [y/n] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            if confirm == "y":
                update_song(
                    song_id,
                    status="identified",
                    final_title=merged["title"],
                    final_artist=merged["artist"],
                    final_album=merged["album"],
                    final_year=merged["year"],
                    id_source="acoustid",
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

def run_acoustid_pass() -> dict:
    """
    Process all no_match songs through AcoustID fingerprinting and
    interactive user verification.

    Returns {processed, accepted, skipped, no_acoustid_match, errors}.
    """
    try:
        _check_prerequisites()
    except RuntimeError as e:
        print(f"{RED}AcoustID prerequisites not met:{RESET}\n{e}")
        return {"processed": 0, "accepted": 0, "skipped": 0,
                "no_acoustid_match": 0, "errors": 0}

    songs = get_songs_by_status("no_match")
    total = len(songs)

    if total == 0:
        print("No no_match songs to process with AcoustID.")
        return {"processed": 0, "accepted": 0, "skipped": 0,
                "no_acoustid_match": 0, "errors": 0}

    print(f"AcoustID pass — {total} no_match song(s)")
    print("[a]ccept  [e]dit  [p]lay  [s]kip  [q]uit\n")

    processed = accepted = skipped = no_acoustid_match = errors = 0

    for i, song in enumerate(songs, 1):
        song_id = song["song_id"]
        name = song["file_path"].split("/")[-1]
        print(f"({i}/{total}) Fingerprinting: {name}")

        if not os.path.exists(song["file_path"]):
            print(f"{YELLOW}[{song_id}] File no longer exists — skipping{RESET}\n")
            processed += 1
            continue

        matches = _lookup(song["file_path"])

        if not matches:
            print(f"{YELLOW}[{song_id}] No AcoustID match — stays no_match{RESET}\n")
            no_acoustid_match += 1
            processed += 1
            continue

        result = _review_match(song, matches[0])
        processed += 1

        if result in ("accepted", "edited"):
            accepted += 1
        elif result == "skipped":
            skipped += 1
        elif result == "quit":
            break

    print(
        f"AcoustID pass complete — {accepted} accepted, {skipped} skipped, "
        f"{no_acoustid_match} no match, {errors} errors."
    )
    return {
        "processed": processed,
        "accepted": accepted,
        "skipped": skipped,
        "no_acoustid_match": no_acoustid_match,
        "errors": errors,
    }
