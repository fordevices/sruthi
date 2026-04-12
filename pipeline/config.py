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
from pathlib import Path

# Load .env file from project root if present (never required — env vars take precedence)
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

INPUT_DIR = "Input"
OUTPUT_DIR = "Music"
DB_PATH = "music.db"
RUNS_DIR = "runs"
SUPPORTED_EXTENSIONS = [".mp3"]
SHAZAM_SLEEP_SEC = 2.0   # seconds to wait between ShazamIO calls
LANGUAGES = ["Tamil", "Hindi", "English", "Other"]

# Sarvam AI API key — register free at https://sarvam.ai
# Required only for the --transliterate pass
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# ACRCloud credentials — register free at https://console.acrcloud.com
# Required only for the --acrcloud pass (select "Recorded Music" project type)
ACRCLOUD_HOST         = os.getenv("ACRCLOUD_HOST", "")
ACRCLOUD_ACCESS_KEY   = os.getenv("ACRCLOUD_ACCESS_KEY", "")
ACRCLOUD_ACCESS_SECRET = os.getenv("ACRCLOUD_ACCESS_SECRET", "")
ACRCLOUD_SLEEP_SEC    = 1.0   # seconds between ACRCloud calls (no documented rate limit beyond daily quota)
