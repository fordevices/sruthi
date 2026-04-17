# Sruthi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sruthi takes a folder of MP3 files — even ones with garbled names and missing information — and turns them into a clean, properly labelled music library organised by language, year, and album. Built for large Tamil and Hindi collections where standard tools fall short.

---

## For music lovers

You have a hard drive full of MP3s with names like `0047_track14.mp3` and no idea what they are. Sruthi listens to each one, figures out the song, fills in the correct title, artist, album, and year, and files it away neatly:

```
Music/
├── Hindi/
│   └── 1994/
│       └── Hum Aapke Hain Koun/
│           └── Didi Tera Dewar Deewana — Lata Mangeshkar.mp3
└── Tamil/
    └── 1987/
        └── Nayakan/
            └── Nila Kaikirathu — S.P. Balasubramaniam.mp3
```

It uses Shazam for mainstream music (no account needed) and ACRCloud for older Indian film music — the Saregama catalog that Shazam misses. For anything left over, it searches iTunes by song name or lets you fill in the details yourself.

**→ [Read the User Guide](DOCS/USER_GUIDE.md) to get started.**

---

## For developers

**Language:** Python 3.10+

**Key dependencies:**
- [ShazamIO](https://github.com/dotX12/ShazamIO) — async Shazam fingerprinting, no API key
- [ACRCloud SDK](https://github.com/acrcloud/acrcloud_sdk_python) — audio fingerprinting against the Saregama/HMV India catalog
- [Mutagen](https://mutagen.readthedocs.io/) — ID3 tag read/write
- [Streamlit](https://streamlit.io/) + [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) — optional NL query GUI

**Architecture:** Four-stage pipeline (identify → review → tag → organise) with a SQLite state store for full resume-safety. All state lives in `music.db` — stop at any point and re-run without reprocessing anything already done. Each identification method (Shazam, ACRCloud, metadata search, manual review) is a self-contained module that reads `no_match` rows and writes `identified` rows. 

**→ [Architecture](DOCS/ARCHITECTURE.md) | [Database schema](DOCS/DATABASE.md) | [Design decisions](DOCS/DESIGN_DECISIONS.md)**

**To contribute:** open an issue at [github.com/fordevices/sruthi/issues](https://github.com/fordevices/sruthi/issues). Label bugs `bug`, feature requests `enhancement`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the PR workflow.

---

## How AI is used

**For identifying songs:** Shazam and ACRCloud both use audio fingerprinting — a form of machine learning — to match a short audio sample against millions of tracks. No prompts, no LLMs; just acoustic pattern matching.

**For the optional search GUI:** The natural language query interface (`streamlit run gui.py`) uses the Claude API to translate plain-English questions into SQL queries against the local database. You ask "show me all Tamil songs from 1981" and Claude figures out the right query. Read-only — nothing in your library is changed.

**For artist name transliteration:** The `--transliterate` pass uses the Sarvam AI API to convert Roman-script artist names to native Tamil or Devanagari script in the ID3 tags. Each unique artist name is sent once and cached locally.

**In development:** This project was built entirely using [Claude Code](https://claude.ai/code) — an AI-assisted development workflow. Architecture decisions, bug fixes, feature design, and documentation were all produced through iterative conversation with Claude rather than written from scratch by hand.

---

## Documentation

| | |
|---|---|
| [User Guide](DOCS/USER_GUIDE.md) | Install, first run, handling unmatched songs, all commands |
| [Architecture](DOCS/ARCHITECTURE.md) | Pipeline design, modules, status flow |
| [Database Reference](DOCS/DATABASE.md) | Schema, song IDs, interruption safety |
| [Design Decisions](DOCS/DESIGN_DECISIONS.md) | Why these tools, trade-offs considered |
| [Releases](DOCS/RELEASES.md) | Version history |
| [Batch Run History](DOCS/BATCH_RUN_HISTORY.md) | Real-world run stats from a 14,000-song collection |
