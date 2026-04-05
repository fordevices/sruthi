"""
Sruthi — collection-fix filename pattern detection
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Extracts album/movie name clues from filenames for songs that ShazamIO could
not identify. Handles patterns common in Indian music file collections:

  Vaseegara (From Minnale).mp3
  Nenjukulle - From Kadal.mp3
  O Saathi Re [From Muqaddar Ka Sikandar].mp3

If a pattern matches, identify.py sets:
  status    = 'identified'   id_source  = 'collection-fix'
  final_title  = cleaned stem  final_album = extracted album name

These songs land in Music/<Language>/Collections/<Album>/ rather than the
year-based path, since no year is known at identification time. If the year
is later resolved via manual review, organizer.py re-routes them on --move.

Docs:
  Collections/ folder in output structure — DOCS/USER_GUIDE.md  (Output folder structure)
  Stage 1 overview                        — DOCS/ARCHITECTURE.md
Issues:
  #4 — collection-fix pattern detection
"""

import re
from pathlib import Path


# Order matters — more specific patterns first.
_PATTERNS = [
    # (from the movie/film/album AlbumName)
    re.compile(r'\(\s*from\s+the\s+(?:movie|film|album)[:\s]+([^)]+)\)', re.IGNORECASE),
    # [from the movie/film/album AlbumName]
    re.compile(r'\[\s*from\s+the\s+(?:movie|film|album)[:\s]+([^\]]+)\]', re.IGNORECASE),
    # (from AlbumName) or (from: AlbumName)
    re.compile(r'\(\s*from[:\s]+([^)]+)\)', re.IGNORECASE),
    # [from AlbumName] or [from: AlbumName]
    re.compile(r'\[\s*from[:\s]+([^\]]+)\]', re.IGNORECASE),
    # Title - from AlbumName  (dash-separated, at end of string)
    re.compile(r'\s[-–—]\s*from\s+(.+)$', re.IGNORECASE),
]


def extract_collection_clue(file_path: str) -> dict | None:
    """
    Try to extract title and album from a filename using collection patterns.

    Returns {'title': str, 'album': str} if a pattern matches and both
    values are non-empty, otherwise returns None.
    """
    stem = Path(file_path).stem  # filename without extension

    for pattern in _PATTERNS:
        m = pattern.search(stem)
        if not m:
            continue

        album = m.group(1).strip().strip('-').strip()
        clean_title = pattern.sub('', stem).strip().strip('-–— ').strip()

        if clean_title and album:
            return {"title": clean_title, "album": album}

    return None
