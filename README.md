# 🎵 Music Pipeline
> Transform a library of mystery MP3s into a perfectly organized, fully tagged collection.
> Supports Tamil, Hindi, English, and any other language — you pre-sort, the pipeline does the rest.

---

## Project status

| Stage | Status | Session |
|---|---|---|
| Design & planning | ✅ Complete | Session 0 |
| Project scaffold + DB layer | ✅ Complete | Session 1 — 2026-03-21 |
| ShazamIO identification | ✅ Complete | Session 2 — 2026-03-21 |
| Manual review CLI | ✅ Complete | Session 3 — 2026-03-21 |
| Mutagen ID3 tagger | ⬜ Not started | Session 4 |
| File organizer | ⬜ Not started | Session 5 |
| Orchestrator + run logging | ⬜ Not started | Session 6 |
| End-to-end test + polish | ⬜ Not started | Session 7 |

---

## What this does

Takes a folder of unknown, badly-named MP3s and runs them through a four-stage pipeline:

```
Input/Tamil/mystery_track.mp3
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Stage 1 — ShazamIO fingerprint + identify          │
│  Stage 2 — Manual review + override (if no match)   │
│  Stage 3 — Mutagen writes ID3 tags into the file    │
│  Stage 4 — File renamed and moved to clean folder   │
└─────────────────────────────────────────────────────┘
        │
        ▼
Music/Tamil/2001/Minnale/01 - Vaseegara.mp3
```

Every file that passes through is recorded in a local SQLite database (`music.db`).
If you stop mid-way through 1000 files, re-running skips everything already processed.

---

## Fingerprinting API — decision and comparison

### Decision: ShazamIO only ✅

After evaluating three options, **ShazamIO** was selected as the sole fingerprinting engine
for this project. The comparison table below explains why.

### Comparison table

| Criterion | AcoustID + MusicBrainz | **ShazamIO** ✅ | ACRCloud |
|---|---|---|---|
| Database size | ~30M fingerprints, ~10M linked to MusicBrainz | **~200M+ tracks** (Shazam's full database) | 150M+ tracks |
| Tamil coverage | Moderate — community-submitted, gaps pre-2000 | **Excellent** — Shazam is widely used in India; Tamil film music well represented | Good — commercial DB, India coverage strong |
| Hindi / Bollywood | Good, some gaps | **Excellent** | Excellent |
| English | Excellent | Excellent | Excellent |
| Cost | Free, register for key at acoustid.org | **100% Free — no key, no signup** | 14-day trial, then paid (pricing hidden behind login) |
| Python install | `pip install pyacoustid` + **fpcalc binary must be OS-installed** | **`pip install shazamio` — nothing else** | SDK available, heavier setup |
| Binary required? | ✅ Yes — Chromaprint (`fpcalc`) must be installed via brew/apt | **❌ No — pure Python + Rust wheel** | No |
| Rate limits | MusicBrainz: strict 1 req/sec | No documented limit; reasonable throttling recommended | Trial limits unlisted |
| Metadata returned | Title, Artist, Album, Year, MusicBrainz IDs | **Title, Artist, Album, Genre, Cover art URL, Apple Music / Spotify links** | Title, Artist, Album, Year, ISRC, UPC |
| Stability | Open spec, very stable | Reverse-engineered — could break if Shazam changes internals (actively maintained since 2021, v0.8.1 Jun 2025) | Commercial SLA |
| Best for | Open-source purists, Western music-heavy libraries | **Indian music libraries, zero-cost, fastest to start** | Commercial apps, highest reliability |

### Why ShazamIO wins for this use case

- Shazam is the dominant music recognition app in India — Tamil and Hindi film music from the
  1970s onward is heavily indexed because millions of Indian users have Shazamed those songs.
- No `fpcalc` binary to install. No API key to register. Just `pip install shazamio` and go.
- The metadata package is richer out of the box — cover art URL is included in the response,
  no separate Cover Art Archive call needed.
- The library has been actively maintained for 4+ years through multiple Shazam API changes,
  which is a reasonable signal of durability for a personal project.

### Honest trade-off

ShazamIO reverse-engineers Shazam's private API. It is not an officially supported integration.
It could break if Apple/Shazam changes their internal endpoints. If that happens, the fallback
plan is to swap in AcoustID + MusicBrainz (the original plan), which requires adding `fpcalc`
and an API key — both remain documented below for reference.

---

## Architecture

### Input convention (you control this)

Before running the pipeline, you place your MP3s into language-named subfolders:

```
Input/
├── Tamil/        ← All Tamil MP3s (nested subfolders are fine)
├── Hindi/        ← All Hindi MP3s
├── English/      ← All English MP3s
└── Other/        ← Anything else
```

The pipeline reads the folder name as the `language` field.
No language detection code needed — you know your collection better than any algorithm.

### Output folder structure

```
Music/
├── Tamil/
│   ├── 2001/
│   │   └── Minnale/
│   │       ├── 01 - Vaseegara.mp3
│   │       └── 02 - Kannazhaga.mp3
│   └── 1997/
│       └── Minsara Kanavu/
│           └── 03 - Ennavale.mp3
├── Hindi/
│   └── 2011/
│       └── Rockstar/
│           └── 05 - Nadaan Parindey.mp3
└── English/
    └── 1973/
        └── Dark Side of the Moon/
            └── 01 - Speak to Me.mp3
```

Pattern: `Music/<Language>/<Year>/<Album>/<TrackNum> - <Title>.mp3`

Missing fields fall back gracefully:
- No year → `Unknown Year`
- No album → `Unknown Album`
- No track number → title only, no number prefix

### Project file structure

```
music_pipeline/
├── pipeline/
│   ├── __init__.py
│   ├── config.py          # Constants, paths, tunable settings
│   ├── db.py              # All SQLite operations (single source of truth)
│   ├── identify.py        # Stage 1 — ShazamIO recognition
│   ├── review.py          # Stage 2 — Interactive manual review CLI
│   ├── tagger.py          # Stage 3 — Mutagen ID3 tag write
│   ├── organizer.py       # Stage 4 — Rename + move to output folder
│   └── runner.py          # Orchestrator — ties all stages, writes run log
├── runs/                  # Auto-created; one timestamped subfolder per run
│   └── 2025-06-10_14-32-00/
│       ├── run.log        # Full stdout/stderr for that run
│       └── summary.json   # { matched, no_match, errors, duration_sec, ... }
├── Input/                 # You drop files here, pre-sorted by language
│   ├── Tamil/
│   ├── Hindi/
│   ├── English/
│   └── Other/
├── Music/                 # Final organized output (auto-created)
├── music.db               # SQLite — the resume-safe state store
├── main.py                # CLI entry point
└── requirements.txt
```

---

## ShazamIO response parsing reference

Derived from live API responses on Tamil, Hindi, and English tracks (2026-03-21).
These are the exact field paths used in `pipeline/identify.py`.

### Full response shape (matched track)

```json
{
  "matches": [...],
  "track": {
    "title":    "<song title>",
    "subtitle": "<artist name>",
    "images": {
      "coverart":   "<JPEG URL 400×400>",
      "coverarthq": "<JPEG URL higher res>",
      "background": "<URL>"
    },
    "genres": {
      "primary": "<genre string>"
    },
    "sections": [
      {
        "type": "SONG",
        "metadata": [
          { "title": "Album",    "text": "<album name>" },
          { "title": "Label",    "text": "<label>" },
          { "title": "Released", "text": "<4-digit year>" }
        ]
      },
      { "type": "RELATED", "url": "..." }
    ],
    "releasedate": "DD-MM-YYYY",
    "isrc": "..."
  }
}
```

### Exact extraction paths

| Field | Path | Notes |
|---|---|---|
| `title` | `out["track"]["title"]` | Always present on a match |
| `artist` | `out["track"]["subtitle"]` | Always present on a match — `subtitle`, not `artist` |
| `genre` | `out["track"]["genres"]["primary"]` | Use `.get()` — absent on some tracks |
| `cover_url` | `out["track"]["images"]["coverart"]` | Use `.get()` — absent on some tracks |
| `album` | Find section where `section["type"] == "SONG"`, iterate `section["metadata"]`, pick item where `item["title"] == "Album"`, return `item["text"]` | Use `.get()` at every level |
| `year` | Same SONG section, item where `item["title"] == "Released"`, return `item["text"]` | Returns 4-digit string e.g. `"1999"` |

### No-match response shape

When Shazam cannot identify the audio, `out.get("track")` returns `None` — the key is absent
entirely from the response dict. The `"matches"` list is empty.

No-match check: `if not out.get("track"): → set status = no_match`

### Parsing notes

- `out["track"]["releasedate"]` exists as `"DD-MM-YYYY"` — **do not use this**. Use the
  `sections` metadata `Released` field instead; it returns just `"YYYY"` which is what we store.
- `subtitle` is the artist field. There is no top-level `"artist"` key on the track object.
- The `sections` list is ordered SONG first, then RELATED, for all matched tracks observed so far.
  However, always iterate and check `section["type"] == "SONG"` explicitly — never assume index 0.
- `out["track"]["images"]["coverarthq"]` is a higher-resolution version of `coverart`.
  We store and use `coverart` (400×400) to keep downloads fast.

### Real-world findings — Session 2

Observed on 22 files (10 Tamil, 7 Hindi, 4 English + 1 no-match English) on 2026-03-21:

| Observation | Example | Impact |
|---|---|---|
| Some tracks have **no album or year** in sections metadata | `max-000001` Fight the Power, `max-000013` Mounamaananeram | Fields stored as `""` — handled correctly by empty-string default |
| Shazam DB can return **obviously wrong years** | `max-000015` Maharajanodu: `shazam_year="1905"` (film is from 1995) | Year warning (⚠) in review CLI is the main catch mechanism |
| 3 of 22 tracks (14%) returned **no_match** | `max-000002` KoRn-Evolution, `max-000014` Sathileelavathy_MarugoMarugo, `max-000020` sattam_naanbaneyennathuuyir | Manual review handles these |
| Match rate **86%** on 1970s–2000s Tamil/Hindi classics | — | Strong; Shazam well-indexed for this era |

**Year sanity thresholds for the review CLI warning (⚠):**
- Flag any `shazam_year` that is a number **< 1940** or **> current calendar year**
- The `1905` case above is the canonical example of a corrupt Shazam DB entry
- Years stored as `""` (missing) do **not** trigger the warning — missing is different from wrong

---

## Database schema

### Table: `songs`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment internal row ID |
| `song_id` | TEXT UNIQUE | Human-readable ID: `max-000001` pattern |
| `file_path` | TEXT | Original absolute path at time of discovery |
| `file_hash` | TEXT | MD5 of file bytes — used for dedup and resume |
| `language` | TEXT | Taken from Input subfolder name (Tamil / Hindi / etc.) |
| `status` | TEXT | `pending` → `identified` → `no_match` → `tagged` → `done` → `error` |
| `shazam_title` | TEXT | Title returned by ShazamIO |
| `shazam_artist` | TEXT | Artist returned by ShazamIO |
| `shazam_album` | TEXT | Album returned by ShazamIO |
| `shazam_year` | TEXT | Year returned by ShazamIO |
| `shazam_genre` | TEXT | Genre returned by ShazamIO |
| `shazam_cover_url` | TEXT | Cover art URL returned by ShazamIO |
| `final_title` | TEXT | Title actually written to tags (after any override) |
| `final_artist` | TEXT | Artist actually written to tags |
| `final_album` | TEXT | Album actually written to tags |
| `final_year` | TEXT | Year actually written to tags |
| `final_genre` | TEXT | Genre actually written to tags |
| `final_path` | TEXT | Absolute path after Stage 4 rename + move |
| `override_used` | INTEGER | 1 if user manually entered metadata, 0 otherwise |
| `override_raw` | TEXT | Raw string the user typed during manual review |
| `run_id` | TEXT | Timestamp of the run that last touched this row |
| `created_at` | TEXT | ISO timestamp — when first discovered |
| `updated_at` | TEXT | ISO timestamp — last status change |
| `error_msg` | TEXT | Last error message if status = `error` |

### Table: `runs`

| Column | Type | Description |
|---|---|---|
| `run_id` | TEXT PK | Timestamp string e.g. `2025-06-10_14-32-00` |
| `started_at` | TEXT | ISO timestamp |
| `finished_at` | TEXT | ISO timestamp (null until complete) |
| `mode` | TEXT | `single` or `folder` |
| `source_path` | TEXT | File or folder that was processed |
| `files_total` | INTEGER | Total MP3s found |
| `files_done` | INTEGER | Successfully completed (status = done) |
| `files_error` | INTEGER | Errors encountered |
| `files_no_match` | INTEGER | Files ShazamIO could not identify |

### Song ID format

Pattern: `max-XXXXXX` (six zero-padded digits)

- Generated at insert time, before any API calls
- Read the current max from the `songs` table, increment by 1
- First file ever processed: `max-000001`
- Stored permanently in the ID3 tag `TXXX:PIPELINE_ID` so it survives file moves

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
                  └──► (user skips) ──► no_match (stays, processed next time)

  any stage can go to ──► error  (retried on next run)
```

---

## CLI usage

```bash
# Process a single file
python main.py Input/Tamil/mystery.mp3

# Process an entire language folder (recursive)
python main.py Input/Tamil/

# Process all language folders at once
python main.py Input/

# Resume — skip files already done (default behaviour, explicit flag for clarity)
python main.py Input/Tamil/ --resume

# After a batch: interactively review all unmatched files
python main.py --review

# Run only one stage (useful for debugging)
python main.py Input/Tamil/ --stage 1   # identify only
python main.py Input/Tamil/ --stage 2   # review only
python main.py Input/Tamil/ --stage 3   # tag only
python main.py Input/Tamil/ --stage 4   # organize only

# Dry run — log everything, write nothing
python main.py Input/Tamil/ --dry-run
```

---

## Manual review format

When ShazamIO cannot identify a file, the review CLI shows:

```
────────────────────────────────────────────
Song ID : max-000042
File    : Input/Tamil/track_017.mp3
Status  : no_match
────────────────────────────────────────────
[p] Play file   [s] Skip   [e] Enter metadata   [q] Quit review
> e

Enter: Title | Artist | Album | Year
> Vaseegara | Bombay Jayashri | Minnale | 2001

Parsed:
  Title  : Vaseegara
  Artist : Bombay Jayashri
  Album  : Minnale
  Year   : 2001
Confirm? [y/n] > y
✓ Saved. Status → identified.
```

The parser splits on `|`, trims whitespace, and is lenient — if you only enter two fields
it maps them as `Title | Artist` and leaves the rest blank.

---

## Run logging

Every invocation auto-creates:

```
runs/YYYY-MM-DD_HH-MM-SS/
    run.log         All console output for this run (append mode)
    summary.json    Machine-readable summary written at end of run
```

`summary.json` example:
```json
{
  "run_id": "2025-06-10_14-32-00",
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

## Prerequisites

```bash
# Python 3.10+ required
python3 --version

# Install dependencies (that's it — no system binaries needed)
pip install shazamio mutagen

# Verify
python3 -c "import shazamio; print('shazamio OK')"
python3 -c "import mutagen; print('mutagen OK')"
```

No API keys. No binary installs. No accounts. Just pip and go.

---

## Build sessions — Claude CLI prompt sequence

Each session below is a self-contained prompt to paste into Claude CLI.
Each one ends with a small verification test so you can confirm it works before moving on.
The design doc (`MUSIC_PIPELINE_DESIGN.md`) and this README are updated at the end of each session.

---

### Session 1 — Scaffold + database layer

**What gets built:** Directory structure, `requirements.txt`, `config.py`, `db.py`, stub `main.py`

**Verification:** Run `python main.py --check` and see DB tables created with correct schema.

```
You are helping me build a Python music organization pipeline. Read the README.md
in this folder before writing any code — it is the source of truth for all design
decisions. Do not deviate from the schema, file structure, or naming conventions
defined there.

Session 1 goal: scaffold the project and build the complete database layer.

Create the following files exactly as the README specifies:
  - requirements.txt  (shazamio, mutagen — nothing else)
  - pipeline/__init__.py  (empty)
  - pipeline/config.py
  - pipeline/db.py
  - main.py  (stub only — just argument parsing and a --check flag for now)

pipeline/config.py must define:
  INPUT_DIR = "Input"
  OUTPUT_DIR = "Music"
  DB_PATH = "music.db"
  RUNS_DIR = "runs"
  SUPPORTED_EXTENSIONS = [".mp3"]
  SHAZAM_SLEEP_SEC = 2.0   # seconds to wait between ShazamIO calls
  LANGUAGES = ["Tamil", "Hindi", "English", "Other"]

pipeline/db.py must implement these functions — no others, no shortcuts:
  get_connection() -> sqlite3.Connection
    Creates music.db and both tables (songs, runs) if they do not exist.
    Returns the connection. Uses WAL journal mode.

  generate_song_id() -> str
    Reads the current MAX song_id from the songs table.
    Parses the 6-digit number, increments by 1.
    Returns "max-XXXXXX" zero-padded to 6 digits.
    First call ever returns "max-000001".

  insert_song(file_path: str, file_hash: str, language: str, run_id: str) -> str
    Inserts a new row with status="pending".
    Calls generate_song_id() to get the song_id.
    Sets created_at and updated_at to current UTC ISO timestamp.
    Returns the generated song_id.

  update_song(song_id: str, **kwargs) -> None
    Updates any columns by name for the given song_id.
    Always updates updated_at to current UTC ISO timestamp.

  get_songs_by_status(status: str) -> list[dict]
    Returns all rows matching the given status as a list of dicts.

  song_exists_by_hash(file_hash: str) -> bool
    Returns True if a row with this file_hash already exists in any status.

  create_run(run_id: str, mode: str, source_path: str) -> None
    Inserts a new row into the runs table with started_at = now.

  finish_run(run_id: str, files_total: int, files_done: int,
             files_error: int, files_no_match: int) -> None
    Updates the run row: sets finished_at = now and the counter fields.

  get_run_summary(run_id: str) -> dict
    Returns the runs row as a dict.

main.py --check must:
  1. Call get_connection() to create the DB
  2. Print the names of all tables found in music.db
  3. Print "DB OK" if both songs and runs tables exist

After writing all files, run:
  pip install -r requirements.txt
  python main.py --check

Paste the exact terminal output here so I can verify it before we continue.
At the end, update the README.md project status table:
  change "Project scaffold + DB layer" from ⬜ Not started to ✅ Complete
  and note the session date.
```

---

### Session 2 — ShazamIO identification (Stage 1)

**What gets built:** `pipeline/identify.py`, file walking, MD5 hashing, ShazamIO calls, DB writes

**Verification:** Run on 3 known MP3s (one Tamil, one Hindi, one English) and confirm DB rows are written correctly.

```
Read README.md before writing any code.

Session 2 goal: build Stage 1 — file discovery and ShazamIO identification.

Create pipeline/identify.py implementing these functions:

  compute_md5(file_path: str) -> str
    Read file in 8KB chunks, return hex MD5 digest.

  detect_language(file_path: str) -> str
    Walk the file_path upward until a folder matching one of config.LANGUAGES is found.
    Return that folder name. If none found, return "Other".

  walk_mp3s(source_path: str) -> list[str]
    Recursively find all files with extensions in config.SUPPORTED_EXTENSIONS.
    Return sorted list of absolute paths.

  identify_file(file_path: str, run_id: str) -> dict
    Full Stage 1 pipeline for one file:
    1. Compute MD5. If song_exists_by_hash → log "already in DB, skipping" → return.
    2. Detect language from path.
    3. insert_song() → get song_id.
    4. Call ShazamIO: out = await shazam.recognize(file_path)
    5. Parse the response:
       - Success path: out["track"] exists
         Extract: title, subtitle (artist), sections[0].metadata fields for album/year/genre
         Also extract: images.coverart for cover URL if present
         Update song row: status="identified", shazam_* fields, run_id
       - No match: update status="no_match"
       - Exception: update status="error", error_msg=str(e)
    6. Sleep config.SHAZAM_SLEEP_SEC between calls.
    7. Return the updated song row as dict.

  run_identification(source_path: str, run_id: str) -> dict
    Walk source_path for MP3s.
    For each file, call identify_file().
    Print a one-line progress update per file:
      [max-000001] Tamil | Vaseegara — Bombay Jayashri ✓
      [max-000002] Tamil | track_017.mp3 — no match ✗
    Return a summary dict: {total, identified, no_match, errors, skipped}.

Important ShazamIO parsing notes:
  - The response structure is: out["track"]["title"], out["track"]["subtitle"] (= artist)
  - Album and year are in out["track"]["sections"] — look for section with "metadata" key
  - Genre is in out["track"]["genres"]["primary"] if present
  - Cover art is in out["track"]["images"]["coverart"] if present
  - Wrap ALL ShazamIO calls in try/except — a failed recognition must never crash the run
  - shazamio is async — use asyncio.run() at the runner level, not inside identify_file

Update main.py to add:
  python main.py <path> --stage 1
  which calls run_identification(path, run_id) and prints the summary.

Test with 3 MP3 files placed in Input/Tamil/, Input/Hindi/, Input/English/.
Run: python main.py Input/ --stage 1
Paste the terminal output.
Update README.md status table: ShazamIO identification → ✅ Complete.
```

---

### Session 3 — Manual review CLI (Stage 2)

**What gets built:** `pipeline/review.py` — interactive terminal UI for no_match files

**Verification:** Manually trigger review on 2-3 no_match rows, confirm DB updates correctly.

```
Read README.md before writing any code.

Session 3 goal: build Stage 2 — the interactive manual review CLI.

Create pipeline/review.py implementing:

  parse_override(raw: str) -> dict
    Input: user-typed string like "Vaseegara | Bombay Jayashri | Minnale | 2001"
    Split on "|", strip whitespace from each part.
    Map positionally: [title, artist, album, year] — any trailing fields ignored.
    If fewer than 4 parts, fill missing fields with empty string.
    Return dict with keys: title, artist, album, year.

  play_file(file_path: str) -> None
    Attempt to play the file using the first available player:
      macOS: afplay
      Linux: mpg123 or mpg321 or ffplay
    Run as subprocess, non-blocking (Popen not run — user presses enter to stop).
    If no player found, print "No audio player found — skipping playback."
    Wrap in try/except — never crash the review session.

  review_one(song: dict) -> str
    Show the review block as specified in README.md manual review format section.
    Present menu: [p] Play  [s] Skip  [e] Enter metadata  [q] Quit
    Loop until valid choice:
      p → call play_file(), re-show menu
      s → return "skipped"
      q → return "quit"
      e → prompt for metadata string → call parse_override() → show parsed result
          → confirm [y/n] → if y: update DB (status="identified", final_* fields,
            override_used=1, override_raw=raw) → return "saved"
          → if n: re-show menu

  run_review(limit: int = None) -> dict
    Fetch all songs where status="no_match" from DB.
    If limit given, only process that many.
    For each: call review_one().
    Track: saved, skipped, quit count.
    If review_one returns "quit" → stop loop immediately.
    Print summary at end.
    Return {reviewed, saved, skipped}.

Add to main.py:
  python main.py --review           → run_review() on all no_match
  python main.py --review --limit 10 → run_review(limit=10)

Verification: manually seed 2 rows with status="no_match" in the DB by running
Stage 1 on some unrecognized audio, then run:
  python main.py --review --limit 2
Walk through the prompts. Paste terminal output.
Update README.md status table: Manual review CLI → ✅ Complete.
```

---

### Session 4 — Mutagen ID3 tagger (Stage 3)

**What gets built:** `pipeline/tagger.py` — writes all metadata into the MP3's ID3 tags

**Verification:** Tag one identified file, open in VLC or check with `mutagen-inspect`, confirm all fields.

```
Read README.md before writing any code.

Session 4 goal: build Stage 3 — Mutagen ID3 tag writing.

Create pipeline/tagger.py implementing:

  tag_file(song: dict, dry_run: bool = False) -> bool
    Takes a song dict (DB row) where status = "identified".
    Uses final_* fields if present, falls back to shazam_* fields.
    Opens the MP3 with mutagen.id3.ID3 (create if no tags: ID3() then file.save()).
    Writes these tags:
      TIT2 = final_title
      TPE1 = final_artist
      TALB = final_album
      TDRC = final_year
      TCON = final_genre
      TXXX:PIPELINE_ID = song_id   ← our permanent tracking tag
    If shazam_cover_url is present and not empty:
      Download the image (requests.get, timeout=10)
      Write APIC tag: encoding=3, mime="image/jpeg", type=3, desc="Cover", data=image_bytes
    If dry_run=True: log what would be written, write nothing, return True.
    On success: call update_song(song_id, status="tagged")
    On any exception: call update_song(song_id, status="error", error_msg=str(e)), return False.
    Return True on success, False on failure.

  run_tagging(dry_run: bool = False) -> dict
    Fetch all songs where status = "identified".
    For each: call tag_file(song, dry_run).
    Print per-file result:
      [max-000001] ✓ tagged  Vaseegara — Bombay Jayashri
      [max-000002] ✗ error   track_017.mp3 — <error message>
    Return {tagged, errors}.

Add requests to requirements.txt (for cover art download).
Add to main.py:
  python main.py --stage 3           → run_tagging()
  python main.py --stage 3 --dry-run → run_tagging(dry_run=True)

Verification: run on at least one identified song.
  python main.py --stage 3 --dry-run   (confirm output looks right)
  python main.py --stage 3             (actually write tags)
Then run: python3 -c "from mutagen.id3 import ID3; print(ID3('your_file.mp3').pprint())"
Paste the output — all tags should be visible.
Update README.md status table: Mutagen ID3 tagger → ✅ Complete.
```

---

### Session 5 — File organizer (Stage 4)

**What gets built:** `pipeline/organizer.py` — renames and moves files to final folder structure

**Verification:** Move 3 tagged files and confirm correct paths in `Music/` and DB.

```
Read README.md before writing any code.

Session 5 goal: build Stage 4 — rename and move files to the organized output folder.

Create pipeline/organizer.py implementing:

  sanitize(name: str) -> str
    Remove or replace characters that are illegal in file/folder names: / \ : * ? " < > |
    Replace each with an underscore. Strip leading/trailing whitespace and dots.
    If result is empty, return "Unknown".

  build_target_path(song: dict) -> str
    Constructs the destination path using final_* fields (falling back to shazam_* then "Unknown X"):
      language = song["language"] or "Other"
      year     = final_year or shazam_year or "Unknown Year"
      album    = final_album or shazam_album or "Unknown Album"
      title    = final_title or shazam_title or song_id
      artist   = final_artist or shazam_artist or ""
      track_num = (not currently in schema — omit number prefix if not present)

    Path pattern:
      {config.OUTPUT_DIR}/{language}/{year}/{album}/{title}.mp3
    All components pass through sanitize().
    If title is empty fall back to the original filename stem.
    Return absolute path string.

  organize_file(song: dict, dry_run: bool = False) -> bool
    Build target path.
    If source path == target path: mark done, return True (already in place).
    If dry_run: log the move, return True.
    Create all parent directories with os.makedirs(exist_ok=True).
    If target path already exists: append " (song_id)" before .mp3 to avoid collision.
    Use shutil.move(source, target).
    On success: call update_song(song_id, status="done", final_path=target)
    On exception: update status="error", error_msg=str(e), return False.
    Return True on success.

  run_organization(dry_run: bool = False) -> dict
    Fetch all songs where status = "tagged".
    For each: call organize_file(song, dry_run).
    Print per-file result:
      [max-000001] ✓ moved  → Music/Tamil/2001/Minnale/Vaseegara.mp3
      [max-000002] ✗ error  → <error message>
    Return {moved, errors}.

Add to main.py:
  python main.py --stage 4           → run_organization()
  python main.py --stage 4 --dry-run → run_organization(dry_run=True)

Verification:
  python main.py --stage 4 --dry-run   (confirm proposed paths look right)
  python main.py --stage 4             (actually move files)
Check that Music/ folder structure matches the README pattern.
Paste the tree output: find Music/ -name "*.mp3"
Update README.md status table: File organizer → ✅ Complete.
```

---

### Session 6 — Orchestrator + run logging

**What gets built:** `pipeline/runner.py` — ties all stages together, writes run log + summary.json

**Verification:** Full pipeline run on a small test batch (5 files), confirm runs/ folder created correctly.

```
Read README.md before writing any code.

Session 6 goal: build the orchestrator and run logging system.

Create pipeline/runner.py implementing:

  setup_run_logging(run_id: str) -> logging.Logger
    Create runs/{run_id}/ directory.
    Configure a logger that writes simultaneously to:
      - Console (stdout) with level INFO
      - runs/{run_id}/run.log (file handler, append mode) with level DEBUG
    Return the logger.

  write_summary(run_id: str, summary: dict) -> None
    Write summary dict as pretty-printed JSON to runs/{run_id}/summary.json.
    Always include: run_id, source_path, started_at, finished_at, duration_sec,
      files_total, files_identified, files_no_match, files_already_done,
      files_tagged, files_moved, files_error, shazam_calls_made.

  run_pipeline(source_path: str, stages: list[int] = None,
               dry_run: bool = False, review_after: bool = False) -> None
    stages defaults to [1, 2, 3, 4] — all stages.
    Generate run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    Call setup_run_logging(run_id).
    Call create_run(run_id, mode, source_path).
    Log "=== Run {run_id} started ===".
    Execute only the requested stages in order:
      1 → run_identification(source_path, run_id)
      2 → run_review() if review_after=True, else skip interactive review in batch mode
      3 → run_tagging(dry_run)
      4 → run_organization(dry_run)
    Accumulate stats across stages.
    Call finish_run() with final counts.
    Call write_summary().
    Log "=== Run {run_id} complete === " + one-line summary.

Update main.py to be the complete CLI entry point:
  python main.py <path>                  → run_pipeline(path)
  python main.py <path> --stage 1        → run_pipeline(path, stages=[1])
  python main.py <path> --dry-run        → run_pipeline(path, dry_run=True)
  python main.py <path> --review-after   → run_pipeline(path, review_after=True)
  python main.py --review                → run_review() standalone
  python main.py --check                 → DB check only

Use argparse. Print usage if no arguments given.

Verification: run the full pipeline on 5 test files:
  python main.py Input/ --dry-run
Confirm:
  1. runs/<timestamp>/ folder created with run.log and summary.json
  2. summary.json contains all expected fields
  3. run.log shows each stage's output
Paste summary.json content.
Update README.md status table: Orchestrator + run logging → ✅ Complete.
```

---

### Session 7 — End-to-end test + polish

**What gets built:** Bug fixes, edge case handling, final README update, verification on a real batch

**Verification:** Full run on at least 20 real files. Review unmatched. Confirm final Music/ structure.

```
Read README.md before writing any code.

Session 7 goal: end-to-end test on real files, fix any bugs found, polish the CLI output.

Run the full pipeline on Input/ (all languages):
  python main.py Input/ --dry-run

Then for real:
  python main.py Input/

Then review unmatched:
  python main.py --review

Then run remaining stages:
  python main.py Input/ --stage 3
  python main.py Input/ --stage 4

Check and fix any of these common issues:
  1. ShazamIO response parsing — some tracks return metadata in slightly different
     schema paths; add defensive .get() with defaults everywhere in identify.py
  2. Filename collisions — if two songs have same title, the (song_id) suffix must
     always be appended correctly without breaking the extension
  3. Unicode in filenames — Tamil/Hindi script in album or title names must survive
     the sanitize() function and os.makedirs() correctly on macOS and Linux
  4. Very short MP3s (<5 sec) — ShazamIO may return an error; catch and set no_match
  5. Cover art download timeouts — confirm 10sec timeout is enforced and failure is
     non-fatal (file still gets tagged without art)

Polish checklist:
  - Progress bar or counter: [12/47] identifying...
  - Color output: green ✓ for success, yellow for no_match, red for error
    (use only ANSI codes, no external libraries)
  - --stats flag: print a summary of music.db without running anything
    (total songs, by status, by language)

Final README.md updates:
  - Mark all sessions ✅ Complete
  - Add a "Known issues / limitations" section with anything discovered during testing
  - Add a "Tips for Tamil/Hindi music" section with any matching patterns found
  - Update the project status table header to show overall completion date

Paste the final Music/ folder tree and the last summary.json.
```

---

## Known issues / limitations

_To be filled in during Session 7._

---

## Tips for Tamil / Hindi music matching

_To be filled in during Session 7 based on real-world results._

---

## Fallback plan — if ShazamIO breaks

ShazamIO reverse-engineers Shazam's private API. If it ever stops working:

1. `pip install pyacoustid`
2. Install Chromaprint: `brew install chromaprint` (macOS) or `sudo apt install libchromaprint-tools` (Linux)
3. Register a free API key at https://acoustid.org (takes 2 minutes)
4. Replace `pipeline/identify.py` — the DB schema, status flow, and all other stages remain identical

The fallback degrades match rate for Indian music (estimated 40–70% vs ShazamIO's ~80–90%),
but everything else — the database, tagging, organization, logging — is unchanged.
