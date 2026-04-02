# Architecture

## Overview

`mp3-organizer-pipeline` is a four-stage Python CLI that transforms unknown MP3 files into
a clean, tagged, and organised music library. Each stage is a separate module with a single
responsibility. All state lives in a local SQLite database (`music.db`), which makes the
pipeline fully resume-safe — you can stop at any point and re-run without reprocessing files
that are already complete.

---

## Pipeline stages

| Stage | Module | Entry function | What it does |
|---|---|---|---|
| 1 | `pipeline/identify.py` | `run_identification()` | Walks source path for MP3s, computes MD5 hash for dedup, calls ShazamIO to fingerprint each file; falls back to collection-fix detection for no_match files |
| 2 | `pipeline/review.py` | `run_review()` | Interactive terminal CLI for `no_match` files — play, skip, or enter metadata manually |
| 3 | `pipeline/tagger.py` | `run_tagging()` | Reads `identified` rows from DB, writes ID3 tags into each MP3 using Mutagen, downloads cover art |
| 4 | `pipeline/organizer.py` | `run_organization()` | Reads `tagged` rows from DB, renames and moves each file to `Music/<Language>/<Year>/<Album>/` or `Music/<Language>/Collections/<Album>/` |

---

## Module responsibilities

**`pipeline/config.py`** — All constants and tunable settings. No logic. Everything else
imports from here. Adding a new constant goes here and nowhere else.

**`pipeline/db.py`** — The single source of truth for all SQLite operations. Every read
and write to `music.db` goes through a function in this module. No other module runs raw
SQL. Exports: `get_connection`, `generate_song_id`, `insert_song`, `update_song`,
`get_songs_by_status`, `song_exists_by_hash`, `create_run`, `finish_run`, `get_run_summary`.

**`pipeline/filename_pass.py`** — Filename-based identification (issue #3). Cleans
filenames (strips track numbers, underscores, brackets), searches MusicBrainz text
search API, and presents up to 3 candidates for interactive user verification.
No API key required. Exports `run_filename_pass()`.
**`pipeline/acoustid_pass.py`** — AcoustID + MusicBrainz fallback identification (issue #2).
Fingerprints files with `fpcalc`, queries the AcoustID API, fetches recording metadata from
MusicBrainz, and presents matches interactively for user verification. Requires `fpcalc`
binary and `ACOUSTID_API_KEY` environment variable. Exports `run_acoustid_pass()`.

**`pipeline/collection.py`** — Collection-fix detection. Applies regex patterns to
filenames to extract song title and album name from conventions like `(from Minnale)` or
`[from Kadal]`. Called by `identify.py` as a fallback when Shazam returns no match.
Exports `extract_collection_clue(file_path)`.

**`pipeline/identify.py`** — Stage 1. Owns file discovery (`walk_mp3s`), MD5 hashing
(`compute_md5`), language detection from path (`detect_language`), ShazamIO calls, the
short-file guard, and the collection-fix fallback. Must never import from `tagger.py` or
`organizer.py`.

**`pipeline/review.py`** — Stage 2. Owns the interactive review loop, override parsing
(`parse_override`), and audio playback (`play_file`). Reads `no_match` rows from DB;
writes `identified` rows back. Must not be called in batch/automated mode.

**`pipeline/tagger.py`** — Stage 3. Owns all Mutagen ID3 operations and cover art
download. Exports `resolve()` (field priority rule) which is also imported by
`organizer.py`. Reads `identified` rows; writes `tagged` rows.

**`pipeline/organizer.py`** — Stage 4. Owns `sanitize()` (filename cleaning), path
construction, and file moves. Imports `resolve()` from `tagger.py`. Reads `tagged` rows;
writes `done` rows and sets `final_path`.

**`pipeline/runner.py`** — Orchestrator. Ties all stages together, manages run logging
(`setup_run_logging`), writes `summary.json` (`write_summary`), and exposes
`run_pipeline()`. Also exports ANSI colour constants (`GREEN`, `YELLOW`, `RED`, `BOLD`,
`RESET`) used by all other modules for terminal output.

**`main.py`** — CLI entry point only. Parses arguments with `argparse` and routes to the
correct function. Contains no business logic. All routing goes through `run_pipeline()` or
the individual stage entry functions.

---

## File structure

```
mp3-organizer-pipeline/
├── pipeline/
│   ├── __init__.py
│   ├── config.py          # Constants, paths, tunable settings
│   ├── acoustid_pass.py   # AcoustID + MusicBrainz fallback (interactive, issue #2)
│   ├── collection.py      # Collection-fix detection (filename pattern extraction)
│   ├── filename_pass.py   # MusicBrainz text search fallback (interactive, issue #3)
│   ├── db.py              # All SQLite operations (single source of truth)
│   ├── identify.py        # Stage 1 — ShazamIO recognition + collection-fix fallback
│   ├── review.py          # Stage 2 — Interactive manual review CLI
│   ├── tagger.py          # Stage 3 — Mutagen ID3 tag write
│   ├── organizer.py       # Stage 4 — Rename + move to output folder
│   └── runner.py          # Orchestrator — ties all stages, writes run log
├── runs/                  # Auto-created; one timestamped subfolder per run
│   └── 2026-03-21_14-32-00/
│       ├── run.log        # Full stdout/stderr for that run
│       └── summary.json   # Machine-readable stats
├── Input/                 # Drop files here, pre-sorted by language
│   ├── Tamil/
│   ├── Hindi/
│   ├── English/
│   └── Other/
├── Music/                 # Final organised output (auto-created)
├── DOCS/                  # Documentation
├── music.db               # SQLite — the resume-safe state store
├── main.py                # CLI entry point
└── requirements.txt
```

---

## Status flow

```
[file discovered]
      │
      ▼
  pending ──► identified ──► tagged ──► done
                  │
                  ▼
              no_match ──► (manual review) ──► identified ──► tagged ──► done
                  │
                  └──► (user skips) ──► no_match (stays, processed next --review)

  any stage can go to ──► error  (retried on next run)
```

| Transition | Triggered by |
|---|---|
| `pending` → `identified` | ShazamIO returns a match in Stage 1 |
| `pending` → `identified` (collection-fix) | Shazam fails but filename contains a `from <Album>` pattern |
| `pending` → `no_match` | Shazam returns no match and no collection pattern found, or file too short (<8s) |
| `pending` → `error` | Unhandled exception in Stage 1 |
| `no_match` → `identified` | User enters metadata in `--review` mode (Stage 2) |
| `identified` → `tagged` | Stage 3 writes ID3 tags successfully |
| `identified` → `error` | Tag write fails in Stage 3 |
| `tagged` → `done` | Stage 4 moves file to `Music/` successfully |
| `tagged` → `error` | File move fails in Stage 4 |
| `error` → any | Automatically retried on the next run |

---

## Input convention

Before running the pipeline, files are placed into language-named subfolders under `Input/`:

```
Input/
├── Tamil/        ← All Tamil MP3s (nested subfolders are fine)
├── Hindi/        ← All Hindi MP3s
├── English/      ← All English MP3s
└── Other/        ← Anything else
```

The pipeline reads the folder name as the `language` field. No language detection is
performed — the user knows their collection better than any algorithm. The language name
becomes the first path component in the output (`Music/<Language>/...`).

---

## Output folder structure

```
Music/<Language>/<Year>/<Album>/<Title>.mp3
```

Real examples:

```
Music/Tamil/1987/Rettai Vaal Kuruvi.../Raja Raja Chozhan.mp3
Music/Hindi/1974/Roti Kapda Aur Makaan/Aaj Ki Raat.mp3
Music/English/1973/Dark Side of the Moon/Speak to Me.mp3
```

Missing fields fall back gracefully:
- No year → `Unknown Year`
- No album → `Unknown Album`
- No title → `song_id` (e.g. `max-000042`)

**Duplicate songs** (same title+artist+language as an already-done song) go to:

```
Music/<Language>/Duplicates/<Album>/<Title> (<song_id>).mp3
```

The song_id suffix distinguishes multiple duplicates of the same track. The original
song's `duplicate_count` in the DB is incremented each time a duplicate is found.
The `--review` command shows a duplicate count warning on affected songs.

**Collection-fix songs** (identified from filename patterns, no year known) go to:

```
Music/<Language>/Collections/<Album>/<Title>.mp3
```

Example:
```
Music/Tamil/Collections/Minnale/Vaseegara.mp3
Music/Hindi/Collections/Muqaddar Ka Sikandar/O Saathi Re.mp3
```

Characters illegal in filenames (`/ \ : * ? " < > |`) are replaced with `_`.
Parentheses, brackets, ampersands, hyphens, exclamation marks, and Unicode (Tamil
script, Hindi script, etc.) are preserved exactly.

---

## Run logging

Every invocation auto-creates a timestamped folder under `runs/`:

```
runs/2026-03-21_14-32-00/
    run.log         All console output for this run (append mode, DEBUG level)
    summary.json    Machine-readable stats written at end of run
```

`summary.json` example:

```json
{
  "run_id": "2026-03-21_14-32-00",
  "source_path": "Input/Tamil/",
  "files_total": 47,
  "files_identified": 31,
  "files_no_match": 12,
  "files_already_done": 4,
  "files_error": 0,
  "duration_sec": 183.4,
  "shazam_calls_made": 43
}
```

---

## CLI reference

| Command | What it does |
|---|---|
| `python3 main.py Input/` | Full pipeline run on a folder (all stages) |
| `python3 main.py Input/ --dry-run` | Preview only — nothing written or moved |
| `python3 main.py Input/ --stage 1` | Identify only |
| `python3 main.py Input/ --stage 3` | Tag only (identified songs) |
| `python3 main.py Input/ --stage 4` | Move only (tagged songs) |
| `python3 main.py Input/ --review-after` | Run pipeline then drop into review |
| `python3 main.py --review` | Review all `no_match` files interactively |
| `python3 main.py --review --flagged` | Review only suspicious-year files |
| `python3 main.py --review --all` | Review every file including matched ones |
| `python3 main.py --review --limit N` | Review only next N unmatched files |
| `python3 main.py --stats` | Print DB summary — no files touched |
| `python3 main.py --check` | Verify DB tables exist — nothing else |
| `python3 main.py --move` | Tag and move all identified songs (stages 3+4, no source needed) |
| `python3 main.py --filename-match` | Filename search pass: query MusicBrainz, review interactively |
| `python3 main.py --acoustid` | AcoustID fallback: fingerprint no_match songs, review interactively |
| `python3 main.py --zeroise` | Clear all songs and runs from the database (asks for confirmation) |

---

## Prerequisites

```bash
# Python 3.10+ required
python3 --version

# Install dependencies (no system binaries needed)
pip install -r requirements.txt

# Verify
python3 main.py --check
```

Expected output:
```
Tables in music.db: ['runs', 'songs', 'sqlite_sequence']
DB OK
```

---

## Links

[README.md](../README.md) | [User Guide](USER_GUIDE.md) | [Database Reference](DATABASE.md) | [Design Decisions](DESIGN_DECISIONS.md)
