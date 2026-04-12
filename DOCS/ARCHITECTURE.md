# Architecture

## Overview

Sruthi is a Python CLI that transforms a folder of unknown or badly-tagged MP3 files
into a clean, fully-tagged, organised music library. It identifies songs by audio
fingerprint, repairs their ID3 tags, and moves them into a `Language/Year/Album/`
folder tree. All state lives in a local SQLite database (`music.db`), making every
run fully resume-safe — stop at any point, re-run the same command, and only
unprocessed files are touched.

---

## Pipeline stages

The core pipeline has four stages that run in sequence:

| Stage | Module | Entry function | What it does |
|---|---|---|---|
| 1 | `pipeline/identify.py` | `run_identification()` | Walks source path for MP3s; MD5-deduplicates; calls ShazamIO to fingerprint each file; falls back to collection-fix pattern detection if Shazam returns no match |
| 2 | `pipeline/review.py` | `run_review()` | Interactive terminal review for `no_match` files — skip, enter metadata manually, or accept a candidate |
| 3 | `pipeline/tagger.py` | `run_tagging()` | Reads `identified` rows from DB; writes ID3 tags into each MP3 with Mutagen; downloads and embeds cover art |
| 4 | `pipeline/organizer.py` | `run_organization()` | Reads `tagged` rows from DB; renames and moves each file to its output path; routes duplicates to `Duplicates/` |

### Optional identification passes

These run independently and operate directly on `no_match` rows already in the database.
Each pass that finds a match sets `status='identified'`; run `--move` afterwards to tag
and file the newly identified songs.

| Pass | Command | Module | What it does |
|---|---|---|---|
| Multi-probe | `--multiprobe` | `pipeline/multiprobe_pass.py` | Re-probes no_match songs at 4 time positions (15/35/55/75% of duration) via Shazam; automated, no review step |
| ACRCloud | `--acrcloud [--language L] [--limit N]` | `pipeline/acrcloud_pass.py` | Audio fingerprint via ACRCloud (Saregama/HMV India catalog); strong pre-2000 Indian coverage; 1,000/day free quota |
| Metadata search | `--metadata-search` | `pipeline/filename_pass.py` | Reads ID3 tags + cleaned filename; searches iTunes; interactive candidate review |

---

## Module responsibilities

**`pipeline/config.py`** — All constants and tunable settings in one place. Every other
module imports from here. Exports `INPUT_DIR`, `OUTPUT_DIR`, `DB_PATH`, `RUNS_DIR`,
`SHAZAM_SLEEP_SEC`, `ACRCLOUD_*`, `SARVAM_API_KEY`, and reads `.env` from the project
root on import if present.

**`pipeline/db.py`** — Single source of truth for all SQLite operations. No other
module runs raw SQL. Manages schema creation and additive column migrations via
`PRAGMA table_info`. Key exports: `get_connection`, `generate_song_id`, `insert_song`,
`update_song`, `get_songs_by_status`, `song_exists_by_hash`, `find_done_duplicate`,
`increment_duplicate_count`, `create_run`, `finish_run`, `get_run_summary`.

**`pipeline/collection.py`** — Collection-fix detection. Applies regex patterns to
filenames to extract a title and album from conventions like `(From Minnale)`,
`[from Kadal]`, or `— from Minnale`. Called by `identify.py` immediately after a
Shazam no-match. Exports `extract_collection_clue(file_path)`.

**`pipeline/identify.py`** — Stage 1. Owns file discovery (`walk_mp3s`), MD5 hashing
(`compute_md5`), language detection from path (`detect_language`), ShazamIO
fingerprinting, the short-file guard (<8 s → `no_match`), the collection-fix fallback,
and path-update logic for renamed `no_match` files. Must never import from `tagger.py`
or `organizer.py`.

**`pipeline/review.py`** — Stage 2. Owns the interactive review loop, override parsing
(`parse_override`), and audio playback (`play_file`). Reads `no_match` rows; writes
`identified` rows back. Supports `--flagged` mode (suspicious year), `--all` mode
(every song), and `--limit N`.

**`pipeline/tagger.py`** — Stage 3. Owns all Mutagen ID3 operations and cover art
download. Exports `resolve()` (field priority: `final_val` > `shazam_val` > fallback),
which `organizer.py` also uses. Records `meta_before` and `meta_after` as JSON to the
DB for audit. Reads `identified` rows; writes `tagged` rows.

**`pipeline/organizer.py`** — Stage 4. Owns `sanitize()` (illegal filename character
replacement), path construction, duplicate detection via `find_done_duplicate()`, and
file moves. Routes songs to standard, `Collections/`, or `Duplicates/` output paths.
Imports `resolve()` from `tagger.py`. Reads `tagged` rows; writes `done` rows with
`final_path`.

**`pipeline/acrcloud_pass.py`** — ACRCloud fingerprint pass (`--acrcloud`). Identifies
`no_match` songs via ACRCloud's Recorded Music database, which includes the Saregama
(HMV India) catalog — the largest archive of pre-2000 Tamil and Hindi film music.
Single probe per song at 35% of duration (quota-efficient). Supports `--language` to
restrict to one language folder and `--limit N` to stay within the 1,000/day free-tier
quota. Sets `id_source='acrcloud'`. Requires `ACRCLOUD_HOST`, `ACRCLOUD_ACCESS_KEY`,
`ACRCLOUD_ACCESS_SECRET`.

**`pipeline/multiprobe_pass.py`** — Multi-probe Shazam pass (`--multiprobe`). Re-attempts
identification on `no_match` songs by probing at four time positions (15%, 35%, 55%, 75%
of duration). Exports a 15-second WAV slice via pydub and calls `shazam.recognize(bytes)`
for each. Stops at first match. Fully automated. Sets `id_source='shazam-multiprobe'`.

**`pipeline/filename_pass.py`** — Metadata search pass (`--metadata-search`). Reads
existing ID3 tags (`TIT2`, `TPE1`) from each `no_match` file; falls back to cleaned
filename when tags are absent. Searches iTunes; presents up to 3 candidates for
interactive verification. No API key required. Sets `id_source='metadata-search'`.

**`pipeline/transliterate.py`** — Transliteration pass (`--transliterate`). Converts
Roman-script artist names to native script (Tamil or Devanagari) in the Artist ID3 tag,
using Sarvam AI. Translates each unique artist name once and caches the result — a name
appearing across 200 songs costs one API call. Requires `SARVAM_API_KEY`.

**`pipeline/runner.py`** — Orchestrator. Ties all four stages together, manages run
logging, writes `summary.json`, and exposes `run_pipeline()`. Also exports ANSI colour
constants (`GREEN`, `YELLOW`, `RED`, `BOLD`, `RESET`) used across all modules.

**`main.py`** — CLI entry point only. Parses arguments with `argparse` and routes to
the correct function or pass. Contains no business logic.

---

## File structure

```
sruthi/
├── pipeline/
│   ├── __init__.py
│   ├── config.py           # Constants, paths, environment variables
│   ├── db.py               # All SQLite operations (single source of truth)
│   ├── identify.py         # Stage 1 — ShazamIO fingerprint + collection-fix
│   ├── review.py           # Stage 2 — Interactive manual review CLI
│   ├── tagger.py           # Stage 3 — Mutagen ID3 tag write + cover art
│   ├── organizer.py        # Stage 4 — Rename + move to output folder
│   ├── runner.py           # Orchestrator — ties all stages, writes run log
│   ├── collection.py       # Collection-fix pattern extraction
│   ├── acrcloud_pass.py    # ACRCloud fingerprint pass (--acrcloud)
│   ├── multiprobe_pass.py  # Multi-probe Shazam pass (--multiprobe)
│   ├── filename_pass.py    # Metadata search pass (--metadata-search)
│   └── transliterate.py    # Artist name transliteration (--transliterate)
├── Archive/                # Archived versions of rewritten docs
├── runs/                   # Auto-created; one timestamped subfolder per run
│   └── 2026-03-21_14-32-00/
│       ├── run.log         # Full console output for that run
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
        │
        ├─── collection-fix pattern found ───────► identified (id_source='collection-fix')
        │
        └─── no match ────────────────────────────► no_match
                  │
                  ├─ --multiprobe hit ──────────────► identified (id_source='shazam-multiprobe')
                  ├─ --acrcloud hit ────────────────► identified (id_source='acrcloud')
                  ├─ --metadata-search accepted ────► identified (id_source='metadata-search')
                  ├─ --review manual entry ─────────► identified (override_used=1)
                  └─ no result / skipped ───────────► no_match (stays, retry later)

        [unhandled exception in Stage 1] ────────► error (auto-retried on next run)

                                        identified
                                             │
                                      Stage 3 (tagger)
                                             │
                                          tagged
                                             │
                                      Stage 4 (organizer)
                                      │         │          │
                                   done      done        done
                                (standard) (Collections/) (Duplicates/)
```

### Status transition reference

| Transition | Triggered by |
|---|---|
| `pending` → `identified` | ShazamIO match |
| `pending` → `identified` | Shazam fails; filename has `from <Album>` pattern (collection-fix) |
| `pending` → `no_match` | Shazam returns no match, no collection pattern |
| `pending` → `no_match` | File duration < 8 seconds |
| `pending` → `error` | Unhandled exception in Stage 1 |
| `no_match` → `identified` | `--multiprobe`, `--acrcloud`, `--metadata-search`, or `--review` |
| `identified` → `tagged` | Stage 3 writes ID3 tags successfully |
| `identified` → `error` | Tag write fails in Stage 3 |
| `tagged` → `done` | Stage 4 moves file to `Music/` |
| `tagged` → `error` | File move fails in Stage 4 |
| `error` → `pending` | Automatically reset on the next run |

---

## Input convention

Files go into language-named subfolders under `Input/` before running Stage 1.
Nested subfolders are fine — `walk_mp3s` recurses. Filenames do not need to be
meaningful.

```
Input/
├── Tamil/     ← all Tamil MP3s
├── Hindi/     ← all Hindi MP3s
├── English/   ← all English MP3s
└── Other/     ← anything else
```

The folder name becomes the `language` field in the DB and the first path component
in the output. No automatic language detection — the user pre-sorts.

---

## Output folder structure

```
Music/<Language>/<Year>/<Album>/<Title> - <Artist>.mp3     ← standard
Music/<Language>/Collections/<Album>/<Title>.mp3           ← collection-fix (no year)
Music/<Language>/Duplicates/<Album>/<Title> (<song_id>).mp3 ← duplicate of done song
```

**Missing field fallbacks:**
- No year → `Unknown Year`
- No album → `Unknown Album`
- No title → `<song_id>` (e.g. `max-000042`)

**Duplicate detection** — before moving, `find_done_duplicate(title, artist, language)`
queries for any already-done song with the same title+artist+language (case-insensitive).
Match → file goes to `Duplicates/` and original's `duplicate_count` is incremented.

**Collection-fix songs** have no year (extracted from filename pattern only), so they
go to `Collections/`. If year is resolved later via review or a subsequent pass, the
file re-routes to the standard path on the next `--move` run.

**Filename sanitisation** — characters illegal in most filesystems (`/ \ : * ? " < > |`)
are replaced with `_`. Tamil and Hindi script, brackets, ampersands, and hyphens are
all preserved.

---

## Database schema

Full schema is in [DATABASE.md](DATABASE.md). Key columns:

| Column | Type | Purpose |
|---|---|---|
| `song_id` | TEXT | Stable unique identifier (`max-NNNNNN`), never changes |
| `file_hash` | TEXT | MD5 of file content — deduplication key |
| `language` | TEXT | Inferred from `Input/<Language>/` folder name |
| `status` | TEXT | `pending` → `identified` → `tagged` → `done` (or `no_match` / `error`) |
| `id_source` | TEXT | `shazam`, `shazam-multiprobe`, `acrcloud`, `metadata-search`, `collection-fix` |
| `final_path` | TEXT | Absolute path after Stage 4 move |
| `meta_before` | TEXT (JSON) | ID3 tags as they existed before Stage 3 wrote them |
| `meta_after` | TEXT (JSON) | Values actually written by Stage 3 |
| `duplicate_count` | INTEGER | How many duplicates of this song have been routed to `Duplicates/` |
| `last_attempt_at` | TEXT | ISO 8601 timestamp of the last identification attempt |

Schema migrations are applied automatically at startup via `PRAGMA table_info` +
`ALTER TABLE` — no manual migration steps when upgrading.

---

## Run logging

Every invocation auto-creates a timestamped folder under `runs/`:

```
runs/2026-03-21_14-32-00/
    run.log         All console output for this run
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
| `python3 main.py --move` | Tag and move all identified songs (stages 3+4) |
| `python3 main.py --review` | Review all `no_match` files interactively |
| `python3 main.py --review --flagged` | Review only suspicious-year files |
| `python3 main.py --review --all` | Review every file including already matched |
| `python3 main.py --review --limit N` | Review only the next N files |
| `python3 main.py --multiprobe` | Re-probe all no_match songs at 4 time positions |
| `python3 main.py --acrcloud` | ACRCloud pass on all no_match songs |
| `python3 main.py --acrcloud --language Tamil` | ACRCloud pass — Tamil only |
| `python3 main.py --acrcloud --language Hindi --limit 366` | ACRCloud pass — Hindi, capped at 366 |
| `python3 main.py --metadata-search` | iTunes metadata search pass, interactive |
| `python3 main.py --transliterate` | Transliterate artist names to native script |
| `python3 main.py --retry-no-match Input/` | Reset all no_match → pending and re-run Stage 1 |
| `python3 main.py --stats` | Language × status grid + disk reconciliation |
| `python3 main.py --check` | Verify DB tables exist |
| `python3 main.py --zeroise` | Clear all songs and runs (requires typing YES) |

---

## Links

[README.md](../README.md) | [User Guide](USER_GUIDE.md) | [Database Reference](DATABASE.md) | [Design Decisions](DESIGN_DECISIONS.md)
