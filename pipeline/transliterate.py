"""
Sruthi — transliteration pass (--transliterate)
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Converts the TPE1 (Artist) ID3 tag for done Tamil and Hindi songs from Roman
script to native script using the Sarvam AI transliterate API.

  Tamil example: "Ilaiyaraaja"    → "இளையராஜா"
  Hindi example: "Lata Mangeshkar" → "लता मंगेशकर"

Only the Artist tag is touched. Filenames, folder names, and all other tags
are unchanged. Each unique (roman_name, language) pair is sent to Sarvam once
and cached in the artist_transliterations table — re-runs and large collections
with repeated artist names incur zero extra API calls.

Compound artist strings (e.g. "A.R. Rahman & Lata Mangeshkar") are split on
' & ' and ', ', each name transliterated independently, then reassembled.

Prerequisite: SARVAM_API_KEY environment variable.
  export SARVAM_API_KEY=your_key_here
  Register free at https://sarvam.ai

Docs:
  Transliteration pass walkthrough  — DOCS/USER_GUIDE.md  (Transliteration pass)
  artist_transliterations table     — DOCS/DATABASE.md
Issues:
  #26 — transliteration pass implementation
  #25 — song-level language detection (open; current detection is folder-based)
"""

import re
import time

import requests
from mutagen.id3 import ID3, ID3NoHeaderError, TPE1

from pipeline import config
from pipeline.db import (
    get_connection,
    get_transliteration,
    set_transliteration,
    update_song,
)
from pipeline.runner import GREEN, RED, YELLOW, RESET
from pipeline.tagger import resolve

SARVAM_URL = "https://api.sarvam.ai/transliterate"
SARVAM_SLEEP_SEC = 0.5   # conservative throttle between API calls

LANG_MAP = {
    "Tamil": "ta-IN",
    "Hindi": "hi-IN",
}

# ---------------------------------------------------------------------------
# Artist string splitting
# ---------------------------------------------------------------------------

def split_artists(artist_str: str) -> list[str]:
    """
    Split a compound artist string into individual names.
    Handles separators: ' & ' and ', '
    e.g. "A.R. Rahman, Mano & K.S. Chithra" → ["A.R. Rahman", "Mano", "K.S. Chithra"]
    """
    parts = re.split(r',\s*|\s*&\s*', artist_str)
    return [p.strip() for p in parts if p.strip()]


def join_artists(names: list[str]) -> str:
    """Reassemble a list of names with ', ' separators."""
    return ", ".join(names)


# ---------------------------------------------------------------------------
# Sarvam API
# ---------------------------------------------------------------------------

def _call_sarvam(name: str, target_lang: str) -> str:
    """
    Call Sarvam transliterate API. Returns transliterated text.
    Raises requests.RequestException on failure.
    """
    resp = requests.post(
        SARVAM_URL,
        headers={
            "Content-Type": "application/json",
            "api-subscription-key": config.SARVAM_API_KEY,
        },
        json={
            "input": name,
            "source_language_code": "en-IN",
            "target_language_code": target_lang,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["transliterated_text"]


# ---------------------------------------------------------------------------
# Per-name transliteration (cache-aware)
# ---------------------------------------------------------------------------

def transliterate_name(name: str, language: str) -> tuple[str, bool]:
    """
    Transliterate one artist name for the given language.
    Returns (native_name, from_cache).
    Raises on Sarvam API failure.
    """
    cached = get_transliteration(name, language)
    if cached is not None:
        return cached, True

    target_lang = LANG_MAP[language]
    native = _call_sarvam(name, target_lang)
    set_transliteration(name, language, native)
    time.sleep(SARVAM_SLEEP_SEC)
    return native, False


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run_transliterate_pass(dry_run: bool = False) -> dict:
    """
    Transliterate the Artist ID3 tag for all done Tamil and Hindi songs.
    Returns {updated, cached, errors, skipped}.
    """
    if not config.SARVAM_API_KEY:
        print("SARVAM_API_KEY is not set. Export it before running --transliterate.")
        print("  export SARVAM_API_KEY=your_key_here")
        return {"updated": 0, "cached": 0, "errors": 0, "skipped": 0}

    conn = get_connection()
    try:
        songs = [
            dict(row) for row in conn.execute(
                """SELECT * FROM songs
                   WHERE status = 'done'
                     AND language IN ('Tamil', 'Hindi')
                     AND final_path IS NOT NULL AND final_path != ''"""
            ).fetchall()
        ]
    finally:
        conn.close()

    if not songs:
        print("No done Tamil/Hindi songs found.")
        return {"updated": 0, "cached": 0, "errors": 0, "skipped": 0}

    print(f"{'DRY RUN — ' if dry_run else ''}Transliterating artist tags for {len(songs)} songs...\n")

    updated = cached_hits = errors = skipped = 0

    for song in songs:
        song_id  = song["song_id"]
        language = song["language"]
        path     = song["final_path"]
        artist_roman = resolve(song.get("final_artist"), song.get("shazam_artist"))

        if not artist_roman:
            skipped += 1
            continue

        names = split_artists(artist_roman)
        native_names = []
        any_from_api = False

        try:
            for name in names:
                native, from_cache = transliterate_name(name, language)
                native_names.append(native)
                if not from_cache:
                    any_from_api = True
        except Exception as e:
            errors += 1
            print(f"{RED}[{song_id}] ✗ error    {artist_roman!r} — {e}{RESET}")
            continue

        artist_native = join_artists(native_names)

        if dry_run:
            label = "cached" if not any_from_api else "api"
            print(f"[{song_id}] ({label}) {language} | {artist_roman!r} → {artist_native!r}")
            if any_from_api:
                updated += 1
            else:
                cached_hits += 1
            continue

        # Write TPE1 tag directly to final_path
        try:
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            tags["TPE1"] = TPE1(encoding=3, text=artist_native)
            tags.save(path)
        except Exception as e:
            errors += 1
            print(f"{RED}[{song_id}] ✗ tag error {path!r} — {e}{RESET}")
            continue

        # Update DB
        update_song(song_id, final_artist=artist_native)

        if any_from_api:
            updated += 1
            print(f"{GREEN}[{song_id}] ✓ api      {language} | {artist_roman!r} → {artist_native!r}{RESET}")
        else:
            cached_hits += 1
            print(f"{YELLOW}[{song_id}] ✓ cached   {language} | {artist_roman!r} → {artist_native!r}{RESET}")

    print()
    print(f"Transliteration complete — {updated} via API, {cached_hits} from cache, "
          f"{errors} errors, {skipped} skipped (no artist).")
    return {"updated": updated, "cached": cached_hits, "errors": errors, "skipped": skipped}
