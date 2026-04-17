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

**→ [Read the User Guide](DOCS/guide/USER_GUIDE.md) to get started.**

---

## For developers

**Language:** Python 3.10+

**Key dependencies:**
- [ShazamIO](https://github.com/dotX12/ShazamIO) — async Shazam fingerprinting, no API key
- [ACRCloud SDK](https://github.com/acrcloud/acrcloud_sdk_python) — audio fingerprinting against the Saregama/HMV India catalog
- [Mutagen](https://mutagen.readthedocs.io/) — ID3 tag read/write
- [Streamlit](https://streamlit.io/) + [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) — optional NL query GUI

**Architecture:** Four-stage pipeline (identify → review → tag → organise) with a SQLite state store for full resume-safety. All state lives in `music.db` — stop at any point and re-run without reprocessing anything already done. Each identification method (Shazam, ACRCloud, metadata search, manual review) is a self-contained module that reads `no_match` rows and writes `identified` rows. 

**→ [Architecture](DOCS/engineering/ARCHITECTURE.md) | [Database schema](DOCS/engineering/DATABASE.md) | [Design decisions](DOCS/engineering/DESIGN_DECISIONS.md)**

**To contribute:** open an issue at [github.com/fordevices/sruthi/issues](https://github.com/fordevices/sruthi/issues). Label bugs `bug`, feature requests `enhancement`. See [DOCS/engineering/CONTRIBUTING.md](DOCS/engineering/CONTRIBUTING.md) for the PR workflow.

---

## How AI is used

**For identifying songs:** Shazam and ACRCloud both use audio fingerprinting — a form of machine learning — to match a short audio sample against millions of tracks. No prompts, no LLMs; just acoustic pattern matching.

**For the optional search GUI:** The natural language query interface (`streamlit run gui.py`) uses the Claude API to translate plain-English questions into SQL queries against the local database. You ask "show me all Tamil songs from 1981" and Claude figures out the right query. Read-only — nothing in your library is changed.

**For artist name transliteration:** The `--transliterate` pass uses the Sarvam AI API to convert Roman-script artist names to native Tamil or Devanagari script in the ID3 tags. Each unique artist name is sent once and cached locally.

**In development:** This project was built entirely using [Claude Code](https://claude.ai/code) — an AI-assisted development workflow. Architecture decisions, bug fixes, feature design, and documentation were all produced through iterative conversation with Claude rather than written from scratch by hand.

### Learning AI development from this project

If you are a developer who wants to start working with AI but are not sure where to begin, Sruthi is a practical starting point. It demonstrates three distinct patterns, each self-contained enough to study on its own:

**1. AI as your development tool**
The entire codebase was built through iterative conversation with Claude Code — no feature was designed in isolation and then handed to an AI to implement. The session notes in `DOCS/ai/` show how architecture decisions, bug investigations, and documentation rewrites actually unfolded. Start with [`DOCS/ai/CLAUDE_CLI_WORKFLOW.md`](DOCS/ai/CLAUDE_CLI_WORKFLOW.md) for the workflow, then read through the prompt history to see how the design evolved.

**2. AI as a feature inside your product**
`gui.py` is a minimal, self-contained example of the Anthropic API in a real application: a natural language query interface that translates plain-English questions into SQL. The core pattern — system prompt with schema context, user message, validated response — is under 30 lines and works the same way in any domain. `pipeline/transliterate.py` shows a second pattern: a single-purpose API call with a local cache so the same request is never sent twice.

**3. AI as a code and documentation reviewer**
`review_docs.py` sends your documentation and source files to Claude, GPT-4o, and Gemini simultaneously and collects independent structured feedback. It is a working template you can adapt to any project: swap the file list and the review prompt, and you have a multi-model review tool for your own codebase. The results for this project are in [`DOCS/ai/PEER_REVIEW.md`](DOCS/ai/PEER_REVIEW.md).

---

## What other AI agents think of this

Claude, GPT-4o, and Gemini were each sent the documentation and key source files independently and asked to review the UX and architecture. No prompts were shared between models.

**→ [Read the multi-model peer review](DOCS/ai/PEER_REVIEW.md)**

---

## Documentation

| | |
|---|---|
| [User Guide](DOCS/guide/USER_GUIDE.md) | Install, first run, handling unmatched songs, all commands |
| [Architecture](DOCS/engineering/ARCHITECTURE.md) | Pipeline design, modules, status flow |
| [Database Reference](DOCS/engineering/DATABASE.md) | Schema, song IDs, interruption safety |
| [Design Decisions](DOCS/engineering/DESIGN_DECISIONS.md) | Why these tools, trade-offs considered |
| [Releases](DOCS/guide/RELEASES.md) | Version history |
| [Batch Run History](DOCS/history/BATCH_RUN_HISTORY.md) | Real-world run stats from a 14,000-song collection |
