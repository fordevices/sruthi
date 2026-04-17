# 🎵 Music Pipeline
> Transform a library of mystery MP3s into a perfectly organized, fully tagged collection.
> Supports Tamil, Hindi, English, and any other language — you pre-sort, the pipeline does the rest.

---

## Project status

| Stage | Status | Session |
|---|---|---|
| Design & planning | ✅ Complete | Session 0 |
| Project scaffold + DB layer | ✅ Complete | Session 1 |
| ShazamIO identification | ✅ Complete | Session 2 |
| Manual review CLI | ✅ Complete | Session 3 |
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

---

## ShazamIO response parsing reference

This section documents the exact ShazamIO response structure so `identify.py` is written
correctly the first time. The response is a nested dict — the paths below are the ones
that matter for this pipeline.

### Happy path (song identified)

```python
out = await shazam.recognize("file.mp3")

# Top-level existence check — if this key is missing, it's a no_match
track = out.get("track")           # None if not recognized

# Core fields
title  = track.get("title", "")            # e.g. "Vaseegara"
artist = track.get("subtitle", "")         # e.g. "Bombay Jayashri"  ← note: subtitle not artist

# Genre — present on most tracks, missing on some
genre  = track.get("genres", {}).get("primary", "")

# Cover art — usually present, sometimes missing
cover  = track.get("images", {}).get("coverart", "")

# Album and year — buried inside sections[].metadata[]
# sections is a list of dicts; iterate to find metadata entries
album = ""
year  = ""
for section in track.get("sections", []):
    for meta in section.get("metadata", []):
        if meta.get("title") == "Album":
            album = meta.get("text", "")
        if meta.get("title") == "Released":
            year = meta.get("text", "")   # e.g. "2001"
```

### Known Tamil / Hindi quirks

- **`subtitle` is the artist field** — not `artist`. This trips up almost everyone the first time.
- **Album is sometimes absent** from metadata even on a successful match. Always use `.get()` with `""` default.
- **Year may be a full date string** like `"2001"` or occasionally `"January 2001"`. Store as-is — the organizer uses it as a folder name, it doesn't need to be numeric.
- **Some Tamil tracks return album name in Tamil script** (Unicode). Keep it — `sanitize()` in Stage 4 handles filesystem safety.
- **`out.get("track")` returning `None`** is the normal no-match signal. Not an error — set status `"no_match"` and move on.
- **Network/timeout exceptions** — wrap every `shazam.recognize()` in `try/except Exception` and set status `"error"`. The 2-second sleep between calls is the primary throttle — do not remove it.

### No-match signal

```python
out = await shazam.recognize("file.mp3")
if not out.get("track"):
    # no_match — normal, not an error
    update_song(song_id, status="no_match")
```

### Real-world findings — Session 2 (22 files, Tamil / Hindi / English mix)

- **Match rate: 86% (19/22)** including 1970s Ilaiyaraaja and classic Hindi film songs.
  Shazam's Indian music coverage is confirmed excellent for this use case.
- **Missing album/year is normal** — two tracks (Fight the Power, Mounamaananeram) had
  no data in `sections.metadata` at all. The empty-string default is correct behaviour,
  not a parsing bug.
- **Bad year data exists in Shazam's own DB** — Maharajanodu (max-000015) returned
  `shazam_year = "1905"` when the film is from 1995. This is a Shazam database error.
  The manual review CLI (Session 3) is the fix — display year prominently so implausible
  values are easy to spot. Anything before ~1930 should visually stand out.
- **No-match files had garbled romanised filenames** — `Sathileelavathy_MarugoMarugo.mp3`
  and `sattam_naanbaneyennathuuyir.mp3`. These are the exact files the review stage exists
  for: listen, Google the lyrics, enter the metadata manually.

---

### Session 2 — ShazamIO identification (Stage 1)

**What gets built:** `pipeline/identify.py`, file walking, MD5 hashing, ShazamIO calls, DB writes

**Verification:** Run on 3 known MP3s (one Tamil, one Hindi, one English) and confirm DB rows are written correctly.

```
Read README.md before writing any code — including the "ShazamIO response parsing
reference" section, which defines the exact field paths to use. Do not guess the
response structure; follow that section precisely.

Session 2 goal: build Stage 1 — file discovery and ShazamIO identification.

Create pipeline/identify.py implementing these functions:

  compute_md5(file_path: str) -> str
    Read file in 8KB chunks, return hex MD5 digest.

  detect_language(file_path: str) -> str
    Convert file_path to an absolute path. Walk its parent directories upward.
    Return the first directory name that matches one of config.LANGUAGES (case-insensitive).
    If none found, return "Other".

  walk_mp3s(source_path: str) -> list[str]
    Recursively find all files whose suffix is in config.SUPPORTED_EXTENSIONS.
    Return sorted list of absolute path strings.

  parse_shazam_response(out: dict) -> dict | None
    Takes the raw ShazamIO response dict.
    If out.get("track") is None or falsy: return None (caller sets no_match).
    Otherwise extract and return a dict with keys:
      title, artist, album, year, genre, cover_url
    Use EXACTLY the field paths from the README parsing reference section.
    All fields default to "" if absent — never raise KeyError.

  identify_file(file_path: str, run_id: str, shazam: Shazam) -> dict
    This is a coroutine (async def).
    1. Compute MD5. If song_exists_by_hash(hash) → log "[SKIP] already in DB" → return {}.
    2. detect_language from path.
    3. insert_song(file_path, hash, language, run_id) → song_id.
    4. Call: out = await shazam.recognize(file_path)
    5. Call parse_shazam_response(out).
       - If result is not None: update_song with status="identified" and all shazam_* fields.
         Also copy shazam_* to final_* fields at this point (final_* = shazam_* as default).
       - If result is None: update_song with status="no_match".
    6. On any exception: update_song with status="error", error_msg=str(e).
    7. Return the updated DB row as dict (call get_songs_by_status and filter, or re-query by song_id).

  run_identification(source_path: str, run_id: str) -> dict
    Create a single Shazam() instance. Reuse it for all files — do not create one per file.
    Walk source_path for MP3s.
    Use asyncio.run() once at the top to drive an inner async function that loops over files
    and awaits identify_file() for each, sleeping config.SHAZAM_SLEEP_SEC between calls.
    Print a one-line result per file immediately after processing:
      [max-000001] ✓ identified  Tamil | Vaseegara — Bombay Jayashri
      [max-000002] ✗ no match    Tamil | track_017.mp3
      [max-000003] ↷ skipped     Tamil | already_done.mp3
    Print a running count: (3/47 files processed)
    Return dict: {total, identified, no_match, errors, skipped}.

Update main.py:
  python main.py <path> --stage 1
  Generates a run_id (timestamp), calls run_identification(path, run_id), prints the summary dict.

Test with 3 MP3 files — at least one Tamil, one Hindi, one English.
Run: python main.py Input/ --stage 1
Paste the complete terminal output.
Then run: python3 -c "
import sqlite3, json
conn = sqlite3.connect('music.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT song_id, language, status, shazam_title, shazam_artist, shazam_album, shazam_year FROM songs').fetchall()
for r in rows: print(dict(r))
"
Paste that output too — confirms every field landed in the DB correctly.
Update README.md status table: ShazamIO identification → ✅ Complete.
```

---

### Session 3 — Manual review CLI (Stage 2)

**What gets built:** `pipeline/review.py` — interactive terminal UI for no_match files

**Verification:** Manually trigger review on 2-3 no_match rows, confirm DB updates correctly.

```
Read README.md before writing any code — including the "Real-world findings — Session 2"
block in the ShazamIO parsing reference section. The review CLI must handle those specific
cases well.

Session 3 goal: build Stage 2 — the interactive manual review CLI.

Create pipeline/review.py implementing:

  parse_override(raw: str) -> dict
    Split on "|", strip whitespace from each part.
    Map positionally: [title, artist, album, year].
    Fewer than 4 parts → fill missing with "".
    Return dict: {title, artist, album, year}.

  play_file(file_path: str) -> None
    Try players in order: afplay (macOS), then mpg123, mpg321, ffplay (Linux).
    Launch as non-blocking subprocess (Popen). Print "Playing... press Enter to stop."
    Wait for Enter, then terminate the process.
    If no player found: print "No audio player found — install mpg123 or ffplay."
    Wrap in try/except — never crash the review session.

  format_song_header(song: dict) -> str
    Returns a formatted display block for one song. Must show ALL of these fields
    clearly, each on its own line:
      Song ID   : max-000015
      File      : Input/Tamil/Maharajanodu.mp3
      Language  : Tamil
      Status    : no_match  (or: identified — showing Shazam match for confirmation)
      ── Shazam match ──
      Title     : Maharajanodu
      Artist    : Ilaiyaraaja, Unnikrishnan & K.S. Chithra
      Album     : [empty if missing — show "(none)" not blank]
      Year      : 1905   ⚠  (flag any year before 1940 or after current year with ⚠)
      Genre     : [value or "(none)"]

    The year warning (⚠) is important — it is the main way to catch Shazam DB errors
    like the 1905 / 1995 case from Session 2.

  review_one(song: dict) -> str
    Print a divider line, then format_song_header(song).
    Print menu: [p] Play  [s] Skip  [e] Edit metadata  [q] Quit
    Loop until resolved:
      p → play_file(), redisplay menu
      s → return "skipped"
      q → return "quit"
      e → print current values, prompt:
            "Enter: Title | Artist | Album | Year  (leave blank to keep current)"
          If user enters blank line → keep all current final_* values, return "kept"
          Otherwise → parse_override(raw) → show parsed result with confirmation:
            Title  : <value>   [CHANGED] or [unchanged]
            Artist : <value>   [CHANGED] or [unchanged]
            Album  : <value>
            Year   : <value>
            Confirm? [y/n]
          y → update_song: status="identified", final_title/artist/album/year from
              parsed (only overwrite fields that are non-empty in the parsed result —
              do not blank out a field the user left empty), override_used=1,
              override_raw=raw → return "saved"
          n → redisplay menu

  run_review(mode: str = "no_match", limit: int = None) -> dict
    mode="no_match" → fetch songs where status="no_match"
    mode="all"      → fetch songs where status IN ("identified","no_match") — lets
                      user review and correct Shazam matches too (e.g. bad year 1905)
    mode="flagged"  → fetch identified songs where shazam_year < "1940" OR
                      shazam_year > current year (the ⚠ cases)
    If limit given, cap at that count.
    Print: "Reviewing X files — [s]kip, [e]dit, [p]lay, [q]uit at any time"
    For each: call review_one(). If returns "quit" → stop immediately.
    Print summary at end: X saved, Y skipped, Z remaining.
    Return {reviewed, saved, skipped}.

Add to main.py:
  python main.py --review               → run_review(mode="no_match")
  python main.py --review --all         → run_review(mode="all")
  python main.py --review --flagged     → run_review(mode="flagged")
  python main.py --review --limit N     → run_review(limit=N)

Verification — run in two passes:

Pass 1: review the 3 no_match files from Session 2
  python main.py --review
  For max-000002 (KoRn-Evolution.mp3): enter "Evolution | Korn | Issues | 1999"
  For max-000014 (Sathileelavathy_MarugoMarugo.mp3): skip for now
  For max-000020 (sattam_naanbaneyennathuuyir.mp3): skip for now

Pass 2: catch the bad year
  python main.py --review --flagged
  Confirm max-000015 Maharajanodu appears with ⚠ on the year.
  Edit it: enter "| | | 1995"  (blank title/artist/album, just fix the year)
  Confirm only shazam_year is corrected; title/artist/album unchanged.

After both passes, run the DB query:
  python3 -c "
  import sqlite3
  conn = sqlite3.connect('music.db')
  conn.row_factory = sqlite3.Row
  rows = conn.execute(
    'SELECT song_id, status, final_title, final_artist, final_year, override_used FROM songs ORDER BY song_id'
  ).fetchall()
  for r in rows: print(dict(r))
  "
Paste the output — confirm max-000002 is now status=identified with override_used=1,
and max-000015 has final_year=1995.
Update README.md status table: Manual review CLI → ✅ Complete.
```

---

### Session 4 — Mutagen ID3 tagger (Stage 3)

**What gets built:** `pipeline/tagger.py` — writes all metadata into the MP3's ID3 tags

**Verification:** Dry-run confirms field values, live run writes tags, mutagen inspect confirms all fields landed.

---

## Mutagen ID3 tagging reference

This section documents the exact tagging approach for `tagger.py`. Read this before
writing any code in Session 4.

### Field priority rule

Every tag write must follow this priority order — never skip a level:

```python
def resolve(final_val, shazam_val, fallback=""):
    if final_val and final_val.strip():
        return final_val.strip()
    if shazam_val and final_val.strip():
        return shazam_val.strip()
    return fallback
```

Use `resolve()` for every field. This means:
- A year corrected during review (e.g. 1905 → 1995) is picked up via `final_year`
- A partial override that left album blank still uses `shazam_album` rather than ""
- The fallback is only used if both are genuinely empty

### Known state coming into Session 4

From Sessions 2 and 3, the DB has these statuses:

| Count | Status | Notes |
|---|---|---|
| 20 | `identified` | Ready to tag — includes override_used rows |
| 2 | `no_match` | max-000014, max-000020 — skip for now, tag later after review |

The 20 `identified` rows include:
- max-000002: `final_*` fields fully set via manual override (override_used=1) — tagger must use `final_*`
- max-000015: `final_year=1995`, all other fields from Shazam — partial override case
- All others: `final_*` copied from `shazam_*` at identify time — both are equivalent

### ID3 tags to write

```python
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TXXX, APIC
from mutagen.id3 import ID3NoHeaderError

try:
    tags = ID3(file_path)
except ID3NoHeaderError:
    tags = ID3()          # file has no tags yet — create fresh

tags["TIT2"] = TIT2(encoding=3, text=title)
tags["TPE1"] = TPE1(encoding=3, text=artist)
tags["TALB"] = TALB(encoding=3, text=album)
tags["TDRC"] = TDRC(encoding=3, text=year)
tags["TCON"] = TCON(encoding=3, text=genre)
tags["TXXX:PIPELINE_ID"] = TXXX(encoding=3, desc="PIPELINE_ID", text=song_id)

tags.save(file_path)
```

`encoding=3` is UTF-8 — required for Tamil and Hindi script in album/title fields.

### Cover art

```python
import requests

if cover_url:
    try:
        resp = requests.get(cover_url, timeout=10)
        resp.raise_for_status()
        tags["APIC:Cover"] = APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,        # 3 = front cover
            desc="Cover",
            data=resp.content
        )
    except Exception:
        pass   # cover art failure is non-fatal — file still gets tagged
```

---

```
Read README.md before writing any code — including the "Mutagen ID3 tagging reference"
section immediately above this prompt. Follow the field priority rule and ID3 patterns
exactly as written there.

Session 4 goal: build Stage 3 — Mutagen ID3 tag writing.

Create pipeline/tagger.py implementing:

  resolve(final_val: str, shazam_val: str, fallback: str = "") -> str
    Implements the field priority rule from the tagging reference section.
    final_val wins if non-empty after strip.
    shazam_val is second choice if non-empty after strip.
    fallback (default "") is last resort.

  tag_file(song: dict, dry_run: bool = False) -> bool
    Takes a song dict (DB row) where status = "identified".
    Build all tag values using resolve():
      title   = resolve(song["final_title"],  song["shazam_title"])
      artist  = resolve(song["final_artist"], song["shazam_artist"])
      album   = resolve(song["final_album"],  song["shazam_album"])
      year    = resolve(song["final_year"],   song["shazam_year"])
      genre   = resolve(song["final_genre"],  song["shazam_genre"])
      cover   = song["shazam_cover_url"] or ""
      song_id = song["song_id"]

    If dry_run=True:
      Print a preview block showing every field that would be written.
      Mark each field as [final_*] or [shazam_*] or [empty] so it is clear which
      source won. Do not write anything. Return True.

    If not dry_run:
      Open MP3 with ID3, create if missing (ID3NoHeaderError → ID3()).
      Write all tags using the exact patterns from the tagging reference.
      Attempt cover art download — failure is non-fatal, log it but continue.
      Call tags.save(file_path).
      On success: update_song(song_id, status="tagged"). Return True.
      On any exception during tag write: update_song(song_id, status="error",
        error_msg=str(e)). Return False.

  run_tagging(dry_run: bool = False) -> dict
    Fetch all songs where status = "identified".
    For each: call tag_file(song, dry_run).
    Print one line per file immediately after processing:
      [max-000001] ✓ tagged   Mounamaananeram — S.P. Balasubrahmanyam & S. Janaki
      [max-000015] ✓ tagged   Maharajanodu — Ilaiyaraaja  (year: 1995 from final_*)
      [max-000002] ✓ tagged   Evolution — Korn  (override)
      [max-000099] ✗ error    track.mp3 — <message>
    Return dict: {tagged, errors, skipped}.

Add requests to requirements.txt.
Add to main.py:
  python main.py --stage 3           → run_tagging()
  python main.py --stage 3 --dry-run → run_tagging(dry_run=True)

Verification — three passes:

Pass 1 — dry run, check field sources
  python main.py --stage 3 --dry-run
  Confirm max-000002 shows [final_*] for title/artist/album/year.
  Confirm max-000015 shows [final_*] for year (1995) and [shazam_*] for title/artist.
  Confirm max-000001 shows [shazam_*] for title/artist and [empty] for album (missing).
  Paste the dry-run output for those three songs.

Pass 2 — live tag write
  python main.py --stage 3
  All 20 identified songs should tag successfully (0 errors expected).
  Paste the summary line.

Pass 3 — inspect a Tamil and an override song
  Pick one Tamil track (e.g. max-000012 Raja Raja Chozhan) and the override track
  (max-000002 Evolution). Run:
    python3 -c "
    from mutagen.id3 import ID3
    for f in ['Input/Tamil/raja_raja_chozhan.mp3', 'Input/English/KoRn-Evolution.mp3']:
        print(f'\\n--- {f} ---')
        print(ID3(f).pprint())
    "
  Confirm: TIT2, TPE1, TALB, TDRC, TCON, TXXX:PIPELINE_ID all present.
  Confirm APIC present if shazam_cover_url was non-empty.
  Paste the output.

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
