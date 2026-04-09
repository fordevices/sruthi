# Architecture

## Overview

Sruthi is a Python CLI that transforms a folder of unknown or badly-named
MP3 files into a clean, fully-tagged, organised music library. The pipeline has four core
stages plus three optional identification passes. All state lives in a local SQLite database
(`music.db`), making the pipeline fully resume-safe — you can stop at any point and re-run
without reprocessing files that are already complete.

---

## Pipeline stages

| Stage | Module | Entry function | What it does |
|---|---|---|---|
| 1 | `pipeline/identify.py` | `run_identification()` | Walks source path for MP3s; computes MD5 hash for dedup; calls ShazamIO to fingerprint each file; falls back to collection-fix detection if Shazam returns no match |
| 2 | `pipeline/review.py` | `run_review()` | Interactive terminal CLI for `no_match` files — play, skip, or enter metadata manually |
| 3 | `pipeline/tagger.py` | `run_tagging()` | Reads `identified` rows from DB; writes ID3 tags into each MP3 using Mutagen; downloads and embeds cover art |
| 4 | `pipeline/organizer.py` | `run_organization()` | Reads `tagged` rows from DB; renames and moves each file to its output path; routes duplicates to `Duplicates/` |

### Optional identification passes

These run independently of the main pipeline and operate directly on `no_match` rows
already in the database:

| Pass | Command | Module | What it does |
|---|---|---|---|
| Multi-probe | `--multiprobe` | `pipeline/multiprobe_pass.py` | Re-probes no_match songs at 4 time positions (15/35/55/75% of duration); automated, no review step |
| Metadata search | `--metadata-search` | `pipeline/filename_pass.py` | Reads ID3 tags + cleaned filename; searches iTunes; interactive candidate review |
| AcoustID | `--acoustid` | `pipeline/acoustid_pass.py` | Audio fingerprint via `fpcalc`; queries AcoustID; interactive candidate review |

After either pass accepts a match, run `--move` to tag and move the newly identified files.

---

## Module responsibilities

**`pipeline/config.py`** — All constants and tunable settings in one place. Every other
module imports from here. Nothing else defines paths, thresholds, or environment variable
names. Exports `ACOUSTID_API_KEY` from environment.

**`pipeline/db.py`** — The single source of truth for all SQLite operations. No other
module runs raw SQL. Manages schema creation, column migrations (via `PRAGMA table_info`),
and all CRUD functions. Key exports: `get_connection`, `generate_song_id`, `insert_song`,
`update_song`, `get_songs_by_status`, `song_exists_by_hash`, `find_done_duplicate`,
`increment_duplicate_count`, `create_run`, `finish_run`, `get_run_summary`.

**`pipeline/collection.py`** — Collection-fix detection. Applies regex patterns to filenames
to extract a song title and album name from conventions like `(From Minnale)`, `[from Kadal]`,
or `— from Minnale`. Called by `identify.py` as a fallback immediately after Shazam returns
no match. Exports `extract_collection_clue(file_path)`.

**`pipeline/identify.py`** — Stage 1. Owns file discovery (`walk_mp3s`), MD5 hashing
(`compute_md5`), language detection from path (`detect_language`), ShazamIO fingerprinting,
the short-file guard (<8 s files → `no_match`), the collection-fix fallback, and the
path-update logic for renamed `no_match` files (same hash, different path → update
`file_path` in DB so later passes can find the file). Must never import from `tagger.py`
or `organizer.py`.

**`pipeline/review.py`** — Stage 2. Owns the interactive review loop, override parsing
(`parse_override`), and audio playback (`play_file`). Reads `no_match` rows from DB; writes
`identified` rows back. Must not be called in batch/automated mode. Supports `--flagged`
mode (year outside 1940–present), `--all` mode (every song), and `--limit N`.

**`pipeline/tagger.py`** — Stage 3. Owns all Mutagen ID3 operations and cover art download.
Exports `resolve()` (field priority rule: `final_val` > `shazam_val` > fallback) which is
also used by `organizer.py`. Records `meta_before` (existing tags as JSON) and `meta_after`
(written values as JSON) to the DB for audit. Reads `identified` rows; writes `tagged` rows.

**`pipeline/organizer.py`** — Stage 4. Owns `sanitize()` (illegal filename character
replacement), path construction, duplicate detection via `find_done_duplicate()`, and file
moves. Routes songs to standard, `Collections/`, or `Duplicates/` output paths. Imports
`resolve()` from `tagger.py`. Reads `tagged` rows; writes `done` rows and sets `final_path`.

**`pipeline/multiprobe_pass.py`** — Multi-probe Shazam pass (`--multiprobe`, issue #32).
Re-attempts identification on `no_match` songs by probing at four time positions (15%,
35%, 55%, 75% of duration). For each probe, exports a 15-second WAV slice via pydub and
calls `shazam.recognize(bytes)`. Stops at first match. Fully automated — no interactive
review. Sets `id_source='shazam-multiprobe'` on match. Skips too-short files.

**`pipeline/filename_pass.py`** — Metadata search pass (`--metadata-search`, issue #3).
Reads existing ID3 tags (`TIT2`, `TPE1`) from each `no_match` file first; falls back to the
cleaned filename when tags are absent. Searches iTunes; presents up to 3 candidates for
interactive verification. No API key or binary required. Sets `id_source='metadata-search'`
on acceptance.

**`pipeline/acoustid_pass.py`** — AcoustID fallback pass (`--acoustid`, issue #2).
Fingerprints files with `fpcalc`, queries the AcoustID API, and presents matches
interactively. Requires the `fpcalc` binary (Chromaprint) and the `ACOUSTID_API_KEY`
environment variable. Sets `id_source='acoustid'` on acceptance.

**`pipeline/runner.py`** — Orchestrator. Ties all four stages together, manages run logging
(`setup_run_logging`), writes `summary.json` (`write_summary`), and exposes `run_pipeline()`.
Also exports ANSI colour constants (`GREEN`, `YELLOW`, `RED`, `BOLD`, `RESET`) used by all
modules for terminal output.

**`main.py`** — CLI entry point only. Parses arguments with `argparse` and routes to the
correct function. Contains no business logic. All pipeline work goes through `run_pipeline()`
or the individual pass entry functions.

---

## File structure

```
sruthi/
├── pipeline/
│   ├── __init__.py
│   ├── config.py           # Constants, paths, environment variables
│   ├── db.py               # All SQLite operations (single source of truth)
│   ├── identify.py         # Stage 1 — ShazamIO + collection-fix fallback
│   ├── review.py           # Stage 2 — Interactive manual review CLI
│   ├── tagger.py           # Stage 3 — Mutagen ID3 tag write + cover art
│   ├── organizer.py        # Stage 4 — Rename + move to output folder
│   ├── runner.py           # Orchestrator — ties all stages, writes run log
│   ├── collection.py       # Collection-fix pattern extraction
│   ├── filename_pass.py    # Metadata search pass (--metadata-search)
│   └── acoustid_pass.py    # AcoustID fingerprint pass (--acoustid)
├── runs/                   # Auto-created; one timestamped subfolder per run
│   └── 2026-03-21_14-32-00/
│       ├── run.log         # Full stdout/stderr for that run
│       └── summary.json    # Machine-readable stats
├── Input/                  # Drop files here, pre-sorted by language
│   ├── Tamil/
│   ├── Hindi/
│   ├── English/
│   └── Other/
├── Music/                  # Final organised output (auto-created)
├── DOCS/                   # Documentation
├── music.db                # SQLite — the resume-safe state store
├── main.py                 # CLI entry point
└── requirements.txt
```

---

## Status flow

```
[file discovered by walk_mp3s]
        │
        ▼
    pending
        │
        ├─── ShazamIO match ──────────────────────► identified (id_source='shazam')
        │                                                │
        ├─── collection-fix pattern found ──────────► identified (id_source='collection-fix')
        │                                                │
        ├─── no Shazam match, no pattern ──────────► no_match
        │         │                                      │
        │         ├─ --multiprobe hit ──────────────► identified (id_source='shazam-multiprobe')
        │         ├─ --metadata-search accepted ────► identified (id_source='metadata-search')
        │         ├─ --acoustid accepted ───────────► identified (id_source='acoustid')
        │         ├─ --review manual entry ─────────► identified (id_source=null, override_used=1)
        │         └─ skipped / no result ───────────► no_match (stays, retry later)
        │                                                │
        └─── unhandled exception ───────────────────► error (retried on next run)
                                                         │
                                               identified
                                                    │
                                             Stage 3 (tagger)
                                                    │
                                                 tagged
                                                    │
                                             Stage 4 (organizer)
                                             │         │         │
                                          done      done       done
                                        (standard) (Collections/) (Duplicates/)
```

### Status transition reference

| Transition | Triggered by |
|---|---|
| `pending` → `identified` | ShazamIO returns a match |
| `pending` → `identified` (collection-fix) | Shazam fails; filename contains a `from <Album>` pattern |
| `pending` → `no_match` | Shazam returns no match and no collection pattern found |
| `pending` → `no_match` (short file) | File duration < 8 seconds |
| `pending` → `error` | Unhandled exception in Stage 1 |
| `no_match` → `identified` | User accepts in `--review`, `--metadata-search`, or `--acoustid`; or `--multiprobe` finds a hit |
| `identified` → `tagged` | Stage 3 writes ID3 tags successfully |
| `identified` → `error` | Tag write fails in Stage 3 |
| `tagged` → `done` | Stage 4 moves file to `Music/` |
| `tagged` → `error` | File move fails in Stage 4 |
| `error` → any | Automatically retried on the next run |

---

## Input convention

Files are placed into language-named subfolders under `Input/` before running Stage 1.
Nested subfolders are fine — `walk_mp3s` recurses. Filenames do not need to be meaningful.

```
Input/
├── Tamil/        ← All Tamil MP3s
├── Hindi/        ← All Hindi MP3s
├── English/      ← All English MP3s
└── Other/        ← Anything else
```

The folder name becomes the `language` field in the DB and the first path component in
the output. No automatic language detection is performed — the user pre-sorts.

---

## Output folder structure

```
Music/<Language>/<Year>/<Album>/<Title>.mp3          ← standard path
Music/<Language>/Collections/<Album>/<Title>.mp3     ← collection-fix (no year known)
Music/<Language>/Duplicates/<Album>/<Title> (<song_id>).mp3  ← duplicate of done song
```

**Standard path examples:**
```
Music/Tamil/1987/Rettai Vaal Kuruvi.../Raja Raja Chozhan.mp3
Music/Hindi/1974/Roti Kapda Aur Makaan/Aaj Ki Raat.mp3
Music/English/1999/Issues/Evolution.mp3
```

**Missing field fallbacks:**
- No year → `Unknown Year`
- No album → `Unknown Album`
- No title → `<song_id>` (e.g. `max-000042`)

**Duplicate detection** — at Stage 4, before moving a file, `find_done_duplicate(title,
artist, language)` queries the DB for any already-done song with the same title+artist+language
(case-insensitive). If a match is found, the file is routed to `Duplicates/` and the original
song's `duplicate_count` is incremented. The `--review` display shows a warning when
`duplicate_count > 0`.

**Collection-fix songs** are identified from filename patterns (e.g. `(From Minnale).mp3`)
when Shazam fails. They are routed to `Collections/` because no year is known. If the year
is later resolved via review or a subsequent identification pass, the file can be re-routed
to the standard year-based path on the next `--move` run.

**Filename sanitization** — characters illegal in most filesystems (`/ \ : * ? " < > |`)
are replaced with `_`. All other characters — including Tamil script, Hindi script,
parentheses, brackets, ampersands, hyphens, and exclamation marks — are preserved.

---

## Database schema

Full schema is documented in [DATABASE.md](DATABASE.md). Key columns added post-initial build:

| Column | Type | Added for | Purpose |
|---|---|---|---|
| `meta_before` | TEXT (JSON) | Issue #7 | ID3 tags as they existed before Stage 3 wrote them |
| `meta_after` | TEXT (JSON) | Issue #7 | Values actually written by Stage 3 |
| `duplicate_count` | INTEGER | Issue #5 | How many duplicates of this song have been routed to Duplicates/ |
| `id_source` | TEXT | Issue #7 | Which pass identified the song: `shazam`, `collection-fix`, `acoustid`, `metadata-search` |
| `last_attempt_at` | TEXT (ISO 8601) | Issue #7 | Timestamp of the last identification attempt |

Schema migrations are applied automatically at startup via `PRAGMA table_info` + `ALTER TABLE`
— no manual migration steps needed when upgrading from an earlier version.

---

## Run logging

Every invocation auto-creates a timestamped folder under `runs/`:

```
runs/2026-03-21_14-32-00/
    run.log         All console output for this run (append mode)
    summary.json    Machine-readable stats written at end of run
```

`summary.json` structure:
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
| `python3 main.py Input/ --stage 1` | Stage 1 only (identify) |
| `python3 main.py Input/ --stage 3` | Stage 3 only (tag identified songs) |
| `python3 main.py Input/ --stage 4` | Stage 4 only (move tagged songs) |
| `python3 main.py Input/ --review-after` | Run pipeline then drop into review |
| `python3 main.py --review` | Review all `no_match` files interactively |
| `python3 main.py --review --flagged` | Review only suspicious-year files |
| `python3 main.py --review --all` | Review every file including matched ones |
| `python3 main.py --review --limit N` | Review only next N unmatched files |
| `python3 main.py --review --folder=PATH` | Review only songs whose path starts with PATH (issue #15 — coming soon) |
| `python3 main.py --stats` | Print DB summary — no files touched |
| `python3 main.py --check` | Verify DB tables exist — nothing else |
| `python3 main.py --move` | Tag and move all identified songs (stages 3+4, no source needed) |
| `python3 main.py --multiprobe` | Multi-probe pass: re-probe all no_match songs at 4 time positions via Shazam, automated |
| `python3 main.py --metadata-search` | Metadata search pass: ID3 tags + filename → iTunes, interactive |
| `python3 main.py --retry-no-match Input/` | Reset all no_match → pending and re-run Stage 1 |
| `python3 main.py --acoustid` | AcoustID pass: audio fingerprint → AcoustID, interactive |
| `python3 main.py --zeroise` | Clear all songs and runs from the database (requires typing YES) |

---

## Prerequisites

```bash
# Python 3.10+
python3 --version

# Install dependencies
pip install -r requirements.txt

# Verify
python3 main.py --check
```

For `--acoustid` only:
```bash
pip install pyacoustid
# macOS:   brew install chromaprint
# Linux:   sudo apt install libchromaprint-tools
export ACOUSTID_API_KEY=your_key_here
```

---

## Links

[README.md](../README.md) | [User Guide](USER_GUIDE.md) | [Database Reference](DATABASE.md) | [Design Decisions](DESIGN_DECISIONS.md)
