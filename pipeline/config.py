"""
Sruthi — pipeline configuration constants
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

All path defaults, supported file types, rate limits, and API key resolution
are defined here. Import this module rather than hard-coding paths or keys
anywhere else in the pipeline.

Docs:
  Installation and API key setup — DOCS/USER_GUIDE.md  (Requirements, Installation)
  Database path reference        — DOCS/DATABASE.md
"""

import os

INPUT_DIR = "Input"
OUTPUT_DIR = "Music"
DB_PATH = "music.db"
RUNS_DIR = "runs"
SUPPORTED_EXTENSIONS = [".mp3"]
SHAZAM_SLEEP_SEC = 2.0   # seconds to wait between ShazamIO calls
LANGUAGES = ["Tamil", "Hindi", "English", "Other"]

# AcoustID API key — register free at https://acoustid.org
ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY", "")

# Sarvam AI API key — register free at https://sarvam.ai
# Required only for the --transliterate pass
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
