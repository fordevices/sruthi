"""
Stage 4 — File organizer.
Path pattern and sanitize rules follow the README "File organization reference" section.
"""

import os
import re
import shutil

from pipeline import config
from pipeline.db import (
    find_done_duplicate,
    get_songs_by_status,
    increment_duplicate_count,
    update_song,
)
from pipeline.runner import GREEN, RED, YELLOW, RESET
from pipeline.tagger import resolve

# ---------------------------------------------------------------------------
# Sanitize (README: File organization reference)
# ---------------------------------------------------------------------------

_ILLEGAL = r'[/\\:*?"<>|]'


def sanitize(name: str) -> str:
    """
    Replace illegal filename characters with '_', collapse multiple underscores,
    strip leading/trailing whitespace and dots. Return 'Unknown' if empty.
    Legal: parentheses, brackets, &, -, ,, !, and all Unicode.
    """
    name = re.sub(_ILLEGAL, '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip(' .')
    return name or 'Unknown'


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------

def build_target_path(song: dict) -> str:
    """
    Construct the destination path for a tagged song.

    Normal pattern:      Music/<Language>/<Year>/<Album>/<Title>.mp3
    Collection (no year): Music/<Language>/Collections/<Album>/<Title>.mp3

    All components pass through sanitize(). Returns absolute path.
    """
    language = song.get("language") or "Other"
    year     = resolve(song.get("final_year"),   song.get("shazam_year"),  "")
    album    = resolve(song.get("final_album"),   song.get("shazam_album"), "Unknown Album")
    title    = resolve(song.get("final_title"),   song.get("shazam_title"), song.get("song_id", "Unknown"))

    if song.get("id_source") == "collection-fix" and not year:
        path = os.path.join(
            config.OUTPUT_DIR,
            sanitize(language),
            "Collections",
            sanitize(album),
            sanitize(title) + ".mp3",
        )
    else:
        path = os.path.join(
            config.OUTPUT_DIR,
            sanitize(language),
            sanitize(year or "Unknown Year"),
            sanitize(album),
            sanitize(title) + ".mp3",
        )
    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Duplicate path construction
# ---------------------------------------------------------------------------

def build_duplicate_path(song: dict) -> str:
    """
    Path for a song identified as a duplicate of one already in Music/.
    Pattern: Music/<Language>/Duplicates/<Album>/<Title> (<song_id>).mp3
    The song_id suffix distinguishes multiple duplicates of the same track.
    """
    language = song.get("language") or "Other"
    album    = resolve(song.get("final_album"),  song.get("shazam_album"),  "Unknown Album")
    title    = resolve(song.get("final_title"),  song.get("shazam_title"),  song.get("song_id", "Unknown"))
    stem     = sanitize(f"{title} ({song['song_id']})")

    path = os.path.join(
        config.OUTPUT_DIR,
        sanitize(language),
        "Duplicates",
        sanitize(album),
        stem + ".mp3",
    )
    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Single-file organizer
# ---------------------------------------------------------------------------

def organize_file(song: dict, dry_run: bool = False) -> bool:
    """
    Move one tagged song to its target path.
    If the same title+artist+language is already done, routes to Duplicates/.
    Returns True on success (or dry_run), False on error.
    """
    song_id = song["song_id"]
    source  = song["file_path"]

    # Check for a semantically identical song already in Music/
    title    = resolve(song.get("final_title"),  song.get("shazam_title"),  "")
    artist   = resolve(song.get("final_artist"), song.get("shazam_artist"), "")
    language = song.get("language", "")

    original = find_done_duplicate(title, artist, language) if (title and artist) else None
    if original:
        target = build_duplicate_path(song)
        if dry_run:
            rel = os.path.relpath(target)
            print(f"[{song_id}] duplicate of {original['song_id']} → would move to {rel}")
            return True
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(source, target)
            update_song(song_id, status="done", final_path=os.path.abspath(target))
            increment_duplicate_count(original["song_id"])
            return True
        except Exception as e:
            update_song(song_id, status="error", error_msg=str(e))
            return False

    target = build_target_path(song)

    # Already in place
    if os.path.abspath(source) == target:
        update_song(song_id, status="done", final_path=target)
        return True

    if dry_run:
        rel = os.path.relpath(target)
        print(f"[{song_id}] would move → {rel}")
        return True

    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)

        # Collision with unexpected file at target path — append song_id
        if os.path.exists(target):
            stem   = sanitize(f"{title or song_id} ({song_id})")
            target = os.path.join(os.path.dirname(target), stem + ".mp3")
            if os.path.exists(target):
                update_song(song_id, status="error", error_msg="collision unresolvable")
                return False

        shutil.move(source, target)
        update_song(song_id, status="done", final_path=os.path.abspath(target))
        return True

    except Exception as e:
        update_song(song_id, status="error", error_msg=str(e))
        return False


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run_organization(dry_run: bool = False) -> dict:
    """
    Organize all songs with status="tagged".
    Returns {moved, errors}.
    """
    songs = get_songs_by_status("tagged")
    moved = errors = 0

    if not songs:
        print("No tagged songs to organize.")
        return {"moved": 0, "errors": 0}

    if dry_run:
        print(f"DRY RUN — would organize {len(songs)} song(s):\n")

    for song in songs:
        song_id = song["song_id"]
        ok = organize_file(song, dry_run=dry_run)

        if dry_run:
            moved += 1  # dry-run always counts as success
            continue

        if ok:
            moved += 1
            final_path = song.get("final_path") or build_target_path(song)
            rel = os.path.relpath(final_path)
            if "Duplicates" in rel:
                print(f"{YELLOW}[{song_id}] ⓓ duplicate → {rel}{RESET}")
            else:
                print(f"{GREEN}[{song_id}] ✓ moved   → {rel}{RESET}")
        else:
            errors += 1
            err = song.get("error_msg", "unknown error")
            print(f"{RED}[{song_id}] ✗ error   → {err}{RESET}")

    print()
    if dry_run:
        print(f"Dry run complete — {moved} song(s) previewed, nothing moved.")
    else:
        print(f"Organization complete — {moved} moved, {errors} errors.")

    return {"moved": moved, "errors": errors}
