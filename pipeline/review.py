"""
Sruthi — Stage 2: interactive manual review
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Terminal UI for reviewing songs that could not be identified automatically.
Supports audio playback (afplay / mpg123 / mpg321 / ffplay) and metadata entry
in the format: Title | Artist | Album | Year. Partial overrides are supported —
empty fields keep existing values.

Review modes:
  no_match — songs where status='no_match' (default)
  all      — all songs regardless of status; useful for bulk correction
  flagged  — identified songs with suspicious shazam_year (outside 1940–present)
             catches Shazam data errors like year=1905 instead of 1995 (issue #16/#17)

Accepted songs are set to status='identified' with override_used=1 so the
tagging and organisation stages pick them up on the next --move run.

Docs:
  Manual review walkthrough — DOCS/USER_GUIDE.md  (Manual review)
  Flagged year handling     — DOCS/USER_GUIDE.md  (Catch bad years from Shazam)
Issues:
  #16, #17 — suspicious year detection and --flagged mode
  #15      — --folder scoping for review queue
"""

import shlex
import subprocess
import sys
from datetime import datetime

from pipeline.db import get_connection, get_songs_by_status, update_song

_DIVIDER = "─" * 44
_CURRENT_YEAR = datetime.now().year


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_override(raw: str) -> dict:
    """Split 'Title | Artist | Album | Year' → dict with those four keys."""
    parts = [p.strip() for p in raw.split("|")]
    keys = ["title", "artist", "album", "year"]
    return {k: parts[i] if i < len(parts) else "" for i, k in enumerate(keys)}


def _year_warning(year_str: str) -> str:
    """Return ' ⚠' if year is present but outside [1940, current_year]."""
    if not year_str:
        return ""
    try:
        y = int(year_str)
        if y < 1940 or y > _CURRENT_YEAR:
            return "  ⚠"
    except ValueError:
        pass
    return ""


def play_file(file_path: str) -> None:
    """Launch an audio player non-blocking; wait for Enter, then stop."""
    players = ["afplay", "mpg123", "mpg321", "ffplay"]
    proc = None
    try:
        for player in players:
            try:
                args = [player, file_path]
                # ffplay needs -nodisp -autoexit suppressed for blocking; run headless
                if player == "ffplay":
                    args = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path]
                proc = subprocess.Popen(
                    args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print(f"Playing via {player}... press Enter to stop.")
                break
            except FileNotFoundError:
                continue
        else:
            print("No audio player found — install mpg123 or ffplay.")
            return
        input()
    except Exception as e:
        print(f"Playback error: {e}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()


def format_song_header(song: dict) -> str:
    """Return a formatted display block for one song."""
    song_id = song.get("song_id", "")
    file_path = song.get("file_path", "")
    language = song.get("language", "")
    status = song.get("status", "")

    shazam_title = song.get("shazam_title") or ""
    shazam_artist = song.get("shazam_artist") or ""
    shazam_album = song.get("shazam_album") or ""
    shazam_year = song.get("shazam_year") or ""
    shazam_genre = song.get("shazam_genre") or ""

    year_warn = _year_warning(shazam_year)

    dup_count = song.get("duplicate_count") or 0
    dup_note  = f"  ⓓ {dup_count} duplicate(s) in Music/Duplicates/" if dup_count else ""

    lines = [
        _DIVIDER,
        f"Song ID  : {song_id}{dup_note}",
        f"File     : {file_path}",
        f"Language : {language}",
        f"Status   : {status}",
        f"── Shazam match ──",
        f"Title    : {shazam_title or '(none)'}",
        f"Artist   : {shazam_artist or '(none)'}",
        f"Album    : {shazam_album or '(none)'}",
        f"Year     : {shazam_year or '(none)'}{year_warn}",
        f"Genre    : {shazam_genre or '(none)'}",
        _DIVIDER,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core review logic
# ---------------------------------------------------------------------------

def review_one(song: dict) -> str:
    """
    Interactive review for one song.
    Returns: "saved" | "kept" | "skipped" | "quit"
    """
    print(format_song_header(song))

    song_id = song["song_id"]
    current = {
        "title": song.get("final_title") or song.get("shazam_title") or "",
        "artist": song.get("final_artist") or song.get("shazam_artist") or "",
        "album": song.get("final_album") or song.get("shazam_album") or "",
        "year": song.get("final_year") or song.get("shazam_year") or "",
    }

    while True:
        print("[p] Play  [s] Skip  [e] Edit metadata  [q] Quit")
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

        if choice == "p":
            play_file(song["file_path"])
            print(format_song_header(song))

        elif choice == "s":
            return "skipped"

        elif choice == "q":
            return "quit"

        elif choice == "e":
            print(f"Current values:")
            print(f"  Title  : {current['title'] or '(none)'}")
            print(f"  Artist : {current['artist'] or '(none)'}")
            print(f"  Album  : {current['album'] or '(none)'}")
            print(f"  Year   : {current['year'] or '(none)'}")
            print("Enter: Title | Artist | Album | Year  (leave blank to keep current)")
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            if not raw:
                print("No changes made.")
                return "kept"

            parsed = parse_override(raw)

            print("Parsed:")
            for key in ["title", "artist", "album", "year"]:
                new_val = parsed[key]
                old_val = current[key]
                tag = "  [CHANGED]" if new_val and new_val != old_val else "  [unchanged]"
                display = new_val if new_val else f"(keeping: {old_val or '(none)'})"
                print(f"  {key.capitalize():<6} : {display}{tag}")

            try:
                confirm = input("Confirm? [y/n] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            if confirm == "y":
                # Only overwrite fields where user provided a non-empty value
                updates = {
                    "status": "identified",
                    "override_used": 1,
                    "override_raw": raw,
                }
                for key in ["title", "artist", "album", "year"]:
                    if parsed[key]:
                        updates[f"final_{key}"] = parsed[key]

                update_song(song_id, **updates)
                print("✓ Saved. Status → identified.")
                return "saved"
            else:
                # Re-show header and menu
                print(format_song_header(song))

        else:
            print("Invalid choice.")


def _fetch_flagged() -> list[dict]:
    """Return identified songs where shazam_year is outside [1940, current_year]."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM songs WHERE status = 'identified'"
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            year_str = d.get("shazam_year") or ""
            if _year_warning(year_str):
                result.append(d)
        return result
    finally:
        conn.close()


def run_review(mode: str = "no_match", limit: int = None) -> dict:
    """
    mode="no_match" → songs where status="no_match"
    mode="all"      → songs where status in ("identified", "no_match")
    mode="flagged"  → identified songs with suspicious shazam_year (⚠ cases)
    """
    if mode == "no_match":
        songs = get_songs_by_status("no_match")
    elif mode == "all":
        songs = get_songs_by_status("identified") + get_songs_by_status("no_match")
        songs.sort(key=lambda s: s["song_id"])
    elif mode == "flagged":
        songs = _fetch_flagged()
    else:
        songs = get_songs_by_status("no_match")

    if limit is not None:
        songs = songs[:limit]

    total = len(songs)
    if total == 0:
        print("Nothing to review.")
        return {"reviewed": 0, "saved": 0, "skipped": 0}

    print(f"Reviewing {total} file(s) — [s]kip, [e]dit, [p]lay, [q]uit at any time")
    print()

    saved = skipped = 0
    reviewed = 0

    for song in songs:
        result = review_one(song)
        reviewed += 1

        if result == "saved":
            saved += 1
        elif result == "skipped":
            skipped += 1
        elif result == "kept":
            pass  # counted as reviewed but neither saved nor skipped
        elif result == "quit":
            break

    remaining = total - reviewed
    print()
    print(f"Done — {saved} saved, {skipped} skipped, {remaining} remaining.")
    return {"reviewed": reviewed, "saved": saved, "skipped": skipped}
