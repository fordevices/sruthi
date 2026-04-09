"""
Sruthi — Multi-probe Shazam pass (issue #32)
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Re-attempts Shazam identification on no_match songs by probing multiple time
positions within each file. Fully automated — no interactive review.

Background
----------
ShazamIO's recognize() sends a ~10-second fingerprint window. For songs longer
than 36 seconds it starts at the midpoint (converter.py:125). For older Tamil
and Hindi film music with long orchestral intros, the chorus — the most
fingerprint-dense section — often falls outside that single window. The Shazam
phone app recognises these tracks because the user holds the phone during the
chorus.

This pass tries up to 4 positions (15%, 35%, 55%, 75% of the song's duration)
and takes the first match. Each probe exports a 15-second WAV slice via pydub
and passes it to shazam.recognize(bytes) — supported by the ShazamIO Rust core
directly. The full audio file is loaded once per song; only the slice is sent.

id_source set to 'shazam-multiprobe' on match.

Docs:
  Design rationale — DOCS/DESIGN_DECISIONS.md  (Multi-probe Shazam strategy)
  Architecture     — DOCS/ARCHITECTURE.md       (Optional identification passes)
"""

import asyncio
import io
from datetime import datetime, timezone
from pathlib import Path

from mutagen.mp3 import MP3, HeaderNotFoundError
from pydub import AudioSegment
from shazamio import Shazam

from pipeline import config
from pipeline.db import get_songs_by_status, update_song
from pipeline.runner import GREEN, YELLOW, RED, RESET


def _parse_shazam_response(out: dict) -> dict | None:
    """
    Parse a raw ShazamIO response. Returns a metadata dict or None if no match.
    Duplicated here (not imported from identify.py) to avoid a circular import
    between identify ↔ runner at module load time.
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

# Probe positions as a fraction of total song duration.
# Covers the song broadly — intro, first verse, chorus, outro regions.
PROBE_POSITIONS = [0.15, 0.35, 0.55, 0.75]

# Seconds of audio sent to Shazam per probe.
PROBE_WINDOW_SEC = 15.0

# Minimum audio remaining after a probe start for the probe to be worthwhile.
MIN_REMAINING_SEC = 8.0


def _get_probe_offsets(duration_sec: float) -> list[float]:
    """
    Return probe start times (in seconds) that have at least MIN_REMAINING_SEC
    of audio after them. Probes too close to the end of the file are dropped.
    """
    offsets = []
    for p in PROBE_POSITIONS:
        start = duration_sec * p
        if start + MIN_REMAINING_SEC <= duration_sec:
            offsets.append(start)
    return offsets


async def _probe_file(file_path: str, shazam: Shazam) -> dict | None:
    """
    Load the audio once, then try each probe position in order.
    Returns the parsed Shazam result dict on the first hit, or None if all miss.
    """
    try:
        duration = MP3(file_path).info.length
    except HeaderNotFoundError:
        duration = 60.0  # not a valid MP3 header — attempt anyway with fallback duration

    offsets = _get_probe_offsets(duration)
    if not offsets:
        return None

    try:
        audio = AudioSegment.from_file(file_path)
    except Exception:
        return None

    for start_sec in offsets:
        try:
            start_ms = int(start_sec * 1000)
            end_ms = int((start_sec + PROBE_WINDOW_SEC) * 1000)
            buf = io.BytesIO()
            audio[start_ms:end_ms].export(buf, format="wav")
            out = await shazam.recognize(buf.getvalue())
            result = _parse_shazam_response(out)
            if result is not None:
                return result
            await asyncio.sleep(config.SHAZAM_SLEEP_SEC)
        except Exception:
            continue

    return None


def run_multiprobe_pass() -> None:
    """
    Run the multi-probe pass on all no_match songs, skipping those that were
    marked no_match because they are too short to fingerprint.

    Identified songs are written back to the DB with id_source='shazam-multiprobe'.
    Run --move afterwards to tag and file them.
    """
    songs = get_songs_by_status("no_match")
    eligible = [
        s for s in songs
        if not (s.get("error_msg") or "").startswith("too short")
    ]
    total = len(eligible)

    if total == 0:
        print("No eligible no_match songs found.")
        return

    print(f"Multi-probe pass: {total} songs, up to {len(PROBE_POSITIONS)} Shazam probes each")
    print()

    identified = 0
    still_no_match = 0

    async def _run():
        nonlocal identified, still_no_match
        shazam = Shazam()

        for i, song in enumerate(eligible, 1):
            song_id = song["song_id"]
            file_path = song["file_path"]
            name = Path(file_path).name
            lang = song.get("language", "")

            if not Path(file_path).exists():
                print(f"{YELLOW}[{song_id}] ⚠ missing     ({i}/{total}) {name}{RESET}")
                still_no_match += 1
                continue

            result = await _probe_file(file_path, shazam)
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
                    id_source="shazam-multiprobe",
                    last_attempt_at=now,
                )
                print(
                    f"{GREEN}[{song_id}] ✓ multiprobe  ({i}/{total}) "
                    f"{lang} | {result['title']} — {result['artist']}{RESET}"
                )
                identified += 1
            else:
                update_song(song_id, status="no_match", last_attempt_at=now)
                print(f"{YELLOW}[{song_id}] ✗ no match    ({i}/{total}) {lang} | {name}{RESET}")
                still_no_match += 1

            if i < total:
                await asyncio.sleep(config.SHAZAM_SLEEP_SEC)

    asyncio.run(_run())

    print()
    print(
        f"Multi-probe complete: {identified} identified, "
        f"{still_no_match} still no_match (of {total} eligible)"
    )
    if identified:
        print("Run --move to tag and file the identified songs.")
