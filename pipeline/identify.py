import asyncio
import hashlib
import os
from pathlib import Path

from shazamio import Shazam

from pipeline import config
from pipeline.db import (
    get_connection,
    insert_song,
    song_exists_by_hash,
    update_song,
)


def compute_md5(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def detect_language(file_path: str) -> str:
    path = Path(os.path.abspath(file_path))
    languages_lower = {lang.lower(): lang for lang in config.LANGUAGES}
    for parent in path.parents:
        if parent.name.lower() in languages_lower:
            return languages_lower[parent.name.lower()]
    return "Other"


def walk_mp3s(source_path: str) -> list[str]:
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
    # 1. Dedup check
    file_hash = compute_md5(file_path)
    if song_exists_by_hash(file_hash):
        print(f"[SKIP] already in DB: {file_path}")
        return {}

    # 2. Language
    language = detect_language(file_path)

    # 3. Insert as pending
    song_id = insert_song(file_path, file_hash, language, run_id)

    # 4 & 5. Shazam call + parse
    try:
        out = await shazam.recognize(file_path)
        result = parse_shazam_response(out)

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
                run_id=run_id,
            )
        else:
            update_song(song_id, status="no_match", run_id=run_id)

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
                    title = song.get("shazam_title", "")
                    artist = song.get("shazam_artist", "")
                    print(f"[{song_id}] ✓ identified  ({i}/{total}) {lang} | {title} — {artist}")
                    counts["identified"] += 1
                elif status == "no_match":
                    print(f"[{song_id}] ✗ no match    ({i}/{total}) {lang} | {name}")
                    counts["no_match"] += 1
                elif status == "error":
                    err = song.get("error_msg", "")
                    print(f"[{song_id}] ! error       ({i}/{total}) {lang} | {name} — {err}")
                    counts["errors"] += 1

            if i < total:
                await asyncio.sleep(config.SHAZAM_SLEEP_SEC)

    asyncio.run(_run())
    return counts
