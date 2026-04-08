"""
Sruthi — pipeline package
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

The pipeline package contains all processing stages and supporting modules
for the Sruthi MP3 library organiser. Import individual modules directly;
this __init__.py is intentionally minimal.

Module map:
  config.py        — path constants, API key resolution, rate limits
  db.py            — SQLite schema, all reads/writes to music.db
  runner.py        — orchestrator: ties stages together, writes run logs
  identify.py      — Stage 1: ShazamIO audio fingerprint identification
  review.py        — Stage 2: interactive manual review CLI
  tagger.py        — Stage 3: Mutagen ID3 tag writer
  organizer.py     — Stage 4: file renamer and mover
  filename_pass.py — --metadata-search: iTunes text search pass
  acoustid_pass.py — --acoustid: AcoustID fingerprint fallback
  transliterate.py — --transliterate: Sarvam AI artist name transliteration
  collection.py    — collection-fix: album clue extraction from filenames

Docs:   DOCS/ARCHITECTURE.md
"""
