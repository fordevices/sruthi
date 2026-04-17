"""
Sruthi — ACRCloud audio fingerprint pass (--acrcloud, issue #33)
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Third-party fingerprint pass targeting pre-2000 Tamil and Hindi film music.
ACRCloud has formal catalog licensing deals with Saregama (formerly HMV India),
which holds the largest archive of pre-2000 Indian film music. These tracks are
absent from Shazam's database but present in ACRCloud's Recorded Music catalog.

Flow per song:
  1. Compute probe start position — 35% of duration (skips intro, lands in
     first verse/chorus region; minimum 10 seconds in)
  2. Call recognize_by_file(file_path, start_seconds, rec_length=12)
  3. On match (status code 0): set status='identified', id_source='acrcloud'
  4. On no result (code 1001): leave as no_match
  5. On quota exceeded (code 3003): stop gracefully, report progress

Fully automated — no interactive review step. Run --move after to tag and file.

Rate limits
-----------
ACRCloud free tier: 1,000 queries/day (resets at midnight UTC = 7pm US Eastern).
Use --limit to stay within quota. Default limit is 900 (10% safety buffer).
With two runs per US calendar day (before and after 7pm EST) you can process
~1,800 songs per day — covering 5,500 no_match songs in about 3 days.

Prerequisites
-------------
  pip install pyacrcloud
  export ACRCLOUD_HOST=identify-ap-southeast-1.acrcloud.com
  export ACRCLOUD_ACCESS_KEY=your_access_key
  export ACRCLOUD_ACCESS_SECRET=your_access_secret

Get credentials free at https://console.acrcloud.com (select Recorded Music project).
The host shown in your project dashboard is the correct value — use it exactly.

Docs:
  Design rationale  — DOCS/DESIGN_DECISIONS.md  (ACRCloud pass strategy)
  Architecture      — DOCS/ARCHITECTURE.md       (Optional identification passes)
  User guide        — DOCS/USER_GUIDE.md          (ACRCloud pass section)
Issues:
  #33 — ACRCloud pass implementation
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import error as ID3Error

from pipeline import config
from pipeline.db import get_songs_by_status, update_song
from pipeline.runner import GREEN, YELLOW, RED, BOLD, RESET

# How far into the song to start the fingerprint probe (fraction of duration).
# 35% lands past most orchestral intros in Indian film music; minimum 10 seconds.
PROBE_FRACTION = 0.35
PROBE_MIN_START_SEC = 10.0

# Seconds of audio to fingerprint per probe. Slightly longer than ACRCloud's
# default (10s) to improve match probability on songs with dense arrangements.
REC_LENGTH_SEC = 12

# ACRCloud status codes
_CODE_SUCCESS = 0
_CODE_NO_RESULT = 1001
_CODE_QUOTA_EXCEEDED = 3003

_DIVIDER = "─" * 52


def _check_credentials() -> None:
    """Raise RuntimeError if any required ACRCloud credential is missing."""
    missing = [v for v in ("ACRCLOUD_HOST", "ACRCLOUD_ACCESS_KEY", "ACRCLOUD_ACCESS_SECRET")
               if not getattr(config, v, "")]
    if missing:
        raise RuntimeError(
            f"Missing ACRCloud credential(s): {', '.join(missing)}\n"
            "Register free at https://console.acrcloud.com then set:\n"
            "  export ACRCLOUD_HOST=identify-ap-southeast-1.acrcloud.com\n"
            "  export ACRCLOUD_ACCESS_KEY=your_access_key\n"
            "  export ACRCLOUD_ACCESS_SECRET=your_access_secret\n"
            "Use the host shown in your ACRCloud project dashboard."
        )


def _make_recognizer():
    """Build and return an ACRCloudRecognizer using credentials from config."""
    from acrcloud.recognizer import ACRCloudRecognizer
    return ACRCloudRecognizer({
        "host": config.ACRCLOUD_HOST,
        "access_key": config.ACRCLOUD_ACCESS_KEY,
        "access_secret": config.ACRCLOUD_ACCESS_SECRET,
        "timeout": 15,
    })


def _probe_start(duration_sec: float) -> int:
    """Return the probe start position in whole seconds (native ext requires int)."""
    return int(max(PROBE_MIN_START_SEC, duration_sec * PROBE_FRACTION))


def _parse_acrcloud_response(raw: str) -> dict | None:
    """
    Parse the JSON string returned by ACRCloudRecognizer.recognize_by_file().
    Returns a metadata dict on success, None on no match, or raises on quota exceeded.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    code = data.get("status", {}).get("code")

    if code == _CODE_QUOTA_EXCEEDED:
        raise QuotaExceededError("ACRCloud daily quota reached — stopping.")

    if code != _CODE_SUCCESS:
        return None

    music = data.get("metadata", {}).get("music", [])
    if not music:
        return None

    track = music[0]  # best match (highest score)
    title = track.get("title", "")
    artists = track.get("artists", [])
    artist = ", ".join(a.get("name", "") for a in artists) if artists else ""
    album = track.get("album", {}).get("name", "")
    release_date = track.get("release_date", "")          # e.g. "1990-01-01"
    year = release_date[:4] if len(release_date) >= 4 else ""
    genres = track.get("genres", [])
    genre = genres[0].get("name", "") if genres else ""

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "year": year,
        "genre": genre,
        "cover_url": "",  # ACRCloud does not return cover art URLs in the free tier
    }


class QuotaExceededError(Exception):
    pass


def run_acrcloud_pass(limit: int = 900, language: str | None = None) -> None:
    """
    Run the ACRCloud fingerprint pass on no_match songs.

    limit:    max songs to process this run. Default 900 to stay safely under
              the 1,000/day free-tier quota.
    language: if given, restrict to songs whose language field matches exactly
              (e.g. "Tamil", "Hindi"). Case-sensitive.
    """
    _check_credentials()

    songs = get_songs_by_status("no_match")
    eligible = [
        s for s in songs
        if not (s.get("error_msg") or "").startswith("too short")
        and s.get("id_source") != "acrcloud"
        and (language is None or s.get("language") == language)
    ]

    if not eligible:
        print("No eligible no_match songs found.")
        return

    to_process = eligible[:limit]
    total = len(to_process)
    skipped_limit = len(eligible) - total

    lang_label = f" [{language}]" if language else ""
    print(f"{BOLD}ACRCloud pass{lang_label}:{RESET} {total} songs (limit={limit}"
          + (f", {skipped_limit} deferred to next run)" if skipped_limit else ")")
    )
    print(_DIVIDER)

    recognizer = _make_recognizer()
    identified = 0
    no_match = 0
    errors = 0

    for i, song in enumerate(to_process, 1):
        song_id = song["song_id"]
        file_path = song["file_path"]
        name = Path(file_path).name
        lang = song.get("language", "")

        if not Path(file_path).exists():
            print(f"{YELLOW}[{song_id}] ⚠ missing     ({i}/{total}) {name}{RESET}")
            no_match += 1
            continue

        try:
            duration = MP3(file_path).info.length
        except (HeaderNotFoundError, ID3Error):
            duration = 60.0

        start_sec = _probe_start(duration)

        try:
            # recognize_by_file chokes on paths with spaces (native C ext issue);
            # reading bytes ourselves and using filebuffer is equivalent and reliable.
            file_bytes = Path(file_path).read_bytes()
            raw = recognizer.recognize_by_filebuffer(file_bytes, start_sec, REC_LENGTH_SEC)
            result = _parse_acrcloud_response(raw)
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
                    final_title=result["title"],
                    final_artist=result["artist"],
                    final_album=result["album"],
                    final_year=result["year"],
                    final_genre=result["genre"],
                    id_source="acrcloud",
                    last_attempt_at=now,
                )
                print(
                    f"{GREEN}[{song_id}] ✓ acrcloud    ({i}/{total}) "
                    f"{lang} | {result['title']} — {result['artist']}{RESET}"
                )
                identified += 1
            else:
                update_song(song_id, status="no_match", id_source="acrcloud", last_attempt_at=now)
                print(f"{YELLOW}[{song_id}] ✗ no match    ({i}/{total}) {lang} | {name}{RESET}")
                no_match += 1

        except QuotaExceededError as e:
            print(f"\n{RED}[QUOTA] {e}{RESET}")
            print(f"Progress so far: {identified} identified, {no_match} no_match, {errors} errors")
            print("Quota resets at midnight UTC (7pm US Eastern). Run again after reset.")
            return

        except Exception as e:
            print(f"{RED}[{song_id}] ! error       ({i}/{total}) {lang} | {name} — {e}{RESET}")
            errors += 1

        if i < total:
            time.sleep(config.ACRCLOUD_SLEEP_SEC)

    print()
    print(_DIVIDER)
    print(
        f"ACRCloud pass complete: {identified} identified, "
        f"{no_match} no_match, {errors} errors (of {total} processed)"
    )
    remaining = len(eligible) - total
    if remaining:
        print(f"{remaining} songs deferred — run again after quota resets (midnight UTC / 7pm EST).")
    if identified:
        print("Run --move to tag and file the identified songs.")
