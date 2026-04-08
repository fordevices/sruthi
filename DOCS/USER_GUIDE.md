# Sruthi — User Guide

> **New to this project?** Start with [What it does](../README.md).
> **Want to understand how it works?** See [Architecture](ARCHITECTURE.md).
> **Questions about MP3s and fingerprinting?** See [Music Files Primer](MUSIC_FILES_PRIMER.md).

Sruthi is an open-source command-line tool for identifying, tagging, and organising large
MP3 collections. It is designed for collections where filenames are garbled or meaningless,
ID3 tags are wrong or empty, and standard tools (beets, MusicBrainz Picard) give poor
coverage — particularly for Tamil, Hindi, and other South Asian music.

Sruthi identifies songs by audio fingerprint via ShazamIO (no API key required), enriches
metadata from iTunes as a fallback, writes correct ID3 tags using Mutagen,
then moves each file into a structured folder tree (`Music/<Language>/<Year>/<Album>/`).
Every file is tracked in a local SQLite database, making the process fully resume-safe —
stop at any point and re-run without reprocessing files already done.

---

## Quick command reference

| Command | What it does | Notes |
|---|---|---|
| `python3 main.py Input/` | Full pipeline — identify, tag, and move everything | Resumes safely if interrupted |
| `python3 main.py Input/ --stage 1` | Identify only (Shazam fingerprinting) | First step on a new batch |
| `python3 main.py --review` | Review unmatched files interactively | After Stage 1 finds `no_match` files |
| `python3 main.py --metadata-search` | Search iTunes using ID3 tags + cleaned filename | Second pass for `no_match` files; no API key needed |
| `python3 main.py --acoustid` | AcoustID audio fingerprint fallback | Requires `fpcalc` binary and AcoustID API key |
| `python3 main.py --move` | Tag and move all identified files | Run after any identification pass |
| `python3 main.py --stats` | Show DB summary (counts, languages, top albums) | No files touched |
| `python3 main.py --review --flagged` | Review only suspicious-year entries | Catches Shazam data errors (e.g. year 1905 → 1995) |
| `python3 main.py --review --folder=PATH` | Review only songs in a specific folder | Issue #15 — coming soon |
| `python3 main.py Input/ --dry-run` | Preview everything — nothing written or moved | Safe to run on a new batch first |
| `python3 main.py --zeroise` | Wipe the database and start fresh | Requires typing `YES` to confirm |
| `python3 main.py --transliterate` | Transliterate artist ID3 tags to native script for Tamil/Hindi songs | Requires `SARVAM_API_KEY` |
| `python3 main.py --transliterate --dry-run` | Preview transliterations without writing any tags | Safe first-run check |
| `streamlit run gui.py` | Launch read-only NL query GUI in browser | Requires `ANTHROPIC_API_KEY` + streamlit — v1.2.0 |

For all flags and combinations see [Full CLI reference](#full-cli-reference) below.

---

## Requirements

| Item | Minimum version | Notes |
|---|---|---|
| Python | 3.10+ | Run `python3 --version` to check |
| pip | any | Comes with Python |
| shazamio | 0.8+ | Installed via pip |
| mutagen | any | Installed via pip |
| requests | any | Installed via pip |
| pyacoustid | any | Installed via pip — required for `--acoustid` pass only |
| fpcalc | 1.4+ | System binary (Chromaprint) — required for `--acoustid` pass only |
| Internet | required | ShazamIO sends audio fingerprints to Shazam's servers |
| Disk space | ~50 MB | For `music.db` + run logs; `Music/` output size varies |

**Core pipeline:** no API keys, no accounts, no system binaries beyond Python itself.

**Optional features:**

| Feature | Requires |
|---|---|
| `--transliterate` (artist name transliteration) | Free Sarvam AI API key — register at [sarvam.ai](https://sarvam.ai); set `SARVAM_API_KEY`. Docs: https://docs.sarvam.ai/api-reference-docs/text/transliterate-text |
| `streamlit run gui.py` (NL query GUI) | Claude API key — set `ANTHROPIC_API_KEY`. Plus `pip install streamlit anthropic` |

---

## Installation

### macOS

1. **Install Python 3.10+** if not already installed.

   Option A — Homebrew (recommended):
   ```
   brew install python
   ```
   Option B — Download the installer from python.org.

2. **Clone the repo:**
   ```
   git clone https://github.com/fordevices/sruthi.git
   cd sruthi
   ```

3. **Create a virtual environment** (recommended — keeps dependencies isolated):
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

5. **Verify:**
   ```
   python3 main.py --check
   ```
   Expected output:
   ```
   Tables in music.db: ['runs', 'songs', 'sqlite_sequence']
   DB OK
   ```

---

### Linux (Ubuntu / Debian)

1. **Install Python 3.10+:**
   ```
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. **Clone the repo:**
   ```
   git clone https://github.com/fordevices/sruthi.git
   cd sruthi
   ```

3. **Create a virtual environment:**
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

5. **Verify:**
   ```
   python3 main.py --check
   ```

---

### Windows

> **Note:** The pipeline runs on Windows but the audio playback feature in `--review` mode
> uses `afplay`/`mpg123`, which are not available on Windows. You can still use all other
> features — you just cannot play files during review. Workaround: open the file in Windows
> Media Player or VLC separately while reviewing.

1. **Install Python 3.10+** from python.org.
   During install: check **"Add Python to PATH"**.

2. **Open Command Prompt or PowerShell, then clone the repo:**
   ```
   git clone https://github.com/fordevices/sruthi.git
   cd sruthi
   ```

3. **Create a virtual environment:**
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

5. **Verify:**
   ```
   python main.py --check
   ```

> **Note:** All commands in the rest of this guide use `python3`. On Windows, use `python` instead.

---

## First-time setup

### Step 1 — Sort your MP3s by language

Before running the pipeline, create language subfolders inside `Input/` and place your MP3s
there. Nested subfolders are fine — the pipeline walks recursively.

```
Input/
├── Tamil/        ← Tamil songs (any filename, any subfolder depth)
├── Hindi/        ← Hindi songs
├── English/      ← English songs
└── Other/        ← anything else
```

You do not need to rename files. The whole point of this tool is that the filenames can be
completely wrong or meaningless.

The folder name becomes the **Language** field in the database and in the output path.
You can use any folder name — Tamil, Hindi, English, Other, Malayalam, Telugu, French — as
long as you are consistent.

---

## Running the pipeline

### Full run — process everything

```
python3 main.py Input/
```

This runs all four stages in sequence:

- **Stage 1** — Fingerprint each file with ShazamIO and look up metadata
- **Stage 2** — (skipped in batch mode — see Manual Review below)
- **Stage 3** — Write ID3 tags into each identified MP3
- **Stage 4** — Rename and move each file to `Music/<Language>/<Year>/<Album>/`

Progress is printed live. Each file gets one line:

```
[max-000012] ✓ identified  (12/47) Tamil | Raja Raja Chozhan — Ilaiyaraaja
[max-000014] ✗ no match    (14/47) Tamil | Sathileelavathy_MarugoMarugo.mp3
```

A timestamped log folder is created automatically:

```
runs/2026-03-21_14-32-00/
    run.log          full output for this run
    summary.json     machine-readable stats
```

### Process a single language folder

```
python3 main.py Input/Tamil/
```

### Process a single file

```
python3 main.py Input/Tamil/mystery_track.mp3
```

### Dry run — see what would happen without moving anything

```
python3 main.py Input/ --dry-run
```

All four stages run in preview mode. No files are moved, no tags are written.
Useful before running on a large new batch.

### Run a specific stage only

```
python3 main.py Input/ --stage 1    ← identify only
python3 main.py Input/ --stage 3    ← tag only (identified songs)
python3 main.py Input/ --stage 4    ← move only (tagged songs)
```

---

## Resuming an interrupted run

The pipeline is fully resume-safe. You can stop it at any time — Ctrl-C, close the terminal
window, or let it fail — and re-run the same command.

**How it works:**

- Every file is identified by its MD5 hash when first discovered
- Files already in the database with `status=done` are skipped instantly
- Files with `status=error` are retried automatically
- Files with `status=no_match` wait for manual review (see below)

For a 1000-file collection at 2 seconds per Shazam call, a full Stage 1 run takes roughly
33 minutes. You can run it overnight, interrupt halfway, and resume the next day. Only
unprocessed files will be touched.

**To check progress at any time without running anything:**

```
python3 main.py --stats
```

Example output:

```
Status breakdown:
  done         847
  no_match      91
  error          3
Language breakdown:
  Tamil        512
  Hindi        298
  English      131
Top albums:
  Unknown Album    47
  Payanangal...    12
  ...
91 files still need review — run: python3 main.py --review
```

---

## Manual review

Some files will not be matched by ShazamIO — usually files where the audio fingerprint is not
in Shazam's database, or files that are too short, noisy, or corrupted. These are saved with
`status=no_match` and held until you review them.

### Review all unmatched files

```
python3 main.py --review
```

For each file you will see:

```
────────────────────────────────────────────
Song ID : max-000042
File    : Input/Tamil/sattam_naanbaneyennathuuyir.mp3
Language: Tamil
Status  : no_match
── Shazam match ──
Title   : (none)
────────────────────────────────────────────
[p] Play  [s] Skip  [e] Edit metadata  [q] Quit
```

**Options:**

| Key | Action |
|---|---|
| `p` | Play the file in your terminal (macOS/Linux only) |
| `s` | Skip this file for now, come back later |
| `e` | Enter metadata manually |
| `q` | Quit review, resume later |

### Entering metadata manually

Press `e`, then type in this format:

```
Title | Artist | Album | Year
```

Examples:

```
Vaseegara | Bombay Jayashri | Minnale | 2001
Nadaan Parindey | Mohit Chauhan | Rockstar | 2011
```

You can leave fields blank to keep existing values:

```
| | | 1995      ← fixes only the year, keeps title/artist/album
```

### Catch bad years from Shazam's own database

Shazam occasionally has wrong year data (for example, 1905 instead of 1995). Run this after
every large batch to surface those:

```
python3 main.py --review --flagged
```

Only shows songs where the year looks implausible (before 1940 or in the future).
Use the partial override `| | | 1995` to correct just the year.

### Other review modes

```
python3 main.py --review --all              ← review every song, not just no_match
python3 main.py --review --limit 20         ← review only the next 20 unmatched files
python3 main.py --review --folder=Music/Tamil/Collections/  ← review songs in a specific folder (issue #15 — coming soon)
```

The `--folder` filter scopes the review queue to songs whose stored path starts with the
given prefix. Useful for correcting metadata on all songs that landed in `Collections/`
or any other specific output folder. Works in combination with `--all`, `--flagged`,
and `--limit`.

---

## Metadata search pass

For files that Shazam failed on, a third pass searches iTunes using the best text
signals available — existing ID3 tags (title, artist) are read from the file first,
with the cleaned filename used as a fallback when tags are absent. No API key or
binary dependency required.

```
python3 main.py --metadata-search
```

For each `no_match` file the pipeline builds a search query and shows up to 3 iTunes
candidates:

```
────────────────────────────────────────────
Song ID  : max-000021
File     : Input/Hindi/01_o_saathi_re.mp3
Language : Hindi
Status   : no_match
Search   : 'o saathi re'
── Candidates ──
  [1]       [iTunes]  O Saathi Re — Kishore Kumar  |  Muqaddar Ka Sikandar  1978
  [2]       [iTunes]  O Saathi Re — Lata Mangeshkar  |  Compilation  1985
  [3]       [iTunes]  O Saathi Re — Kishore Kumar  |  Muqaddar Ka Sikandar  1978
────────────────────────────────────────────
[1/2/3] Pick  [e] Edit manually  [p] Play  [s] Skip  [q] Quit

### Running on already-identified files

By default `--metadata-search` only processes `no_match` files. To run it across
every file in the database — useful for correcting wrong years or album names on
files that Shazam already identified — add `--all`:

```
python3 main.py --metadata-search --all
```

To limit to one language folder:

```
python3 main.py --metadata-search --all --folder Tamil
```

After making corrections, run `--move` to rewrite the ID3 tags and relocate any
files whose metadata changed:

```
python3 main.py --move
```
## AcoustID fallback pass

For songs that Shazam could not identify and that have no collection pattern in their
filename, you can run a second identification pass using AcoustID.

### Prerequisites

1. **Install the Python library:**
   ```
   pip install pyacoustid
   ```
   > If you installed dependencies with `pip install -r requirements.txt` before this
   > feature was added, re-run it to pick up `pyacoustid`.

2. **Install Chromaprint** (the `fpcalc` binary used for audio fingerprinting):
   ```
   macOS:   brew install chromaprint
   Linux:   sudo apt install libchromaprint-tools
   Windows: download fpcalc from https://acoustid.org/chromaprint
   ```

3. **Register for a free AcoustID API key** at https://acoustid.org (2 minutes, no payment).

4. **Set the environment variable** (add to `~/.bashrc` to make it permanent):
   ```
   export ACOUSTID_API_KEY=your_key_here
   ```

### Running the pass

```
python3 main.py --acoustid
```

This works directly on your existing `no_match` files in the database — no need to
re-run Stage 1. If you want to test on a small set first:

```
python3 main.py --zeroise                 # wipe DB
python3 main.py Input/Tamil/some_folder/  # re-run Stage 1 on a small folder
python3 main.py --acoustid                # test on that small batch
```

For each `no_match` file, the pipeline will:
- Fingerprint the audio using `fpcalc`
- Query AcoustID and retrieve the best matching recording
- Show you the proposed match with a confidence percentage

```
────────────────────────────────────────────
Song ID  : max-000014
File     : Input/Tamil/mystery.mp3
Language : Tamil
── AcoustID match  (confidence: 94%) ──
Title    : Vaseegara
Artist   : Bombay Jayashri
Album    : Minnale
Year     : 2001
────────────────────────────────────────────
[a] Accept  [e] Edit  [p] Play  [s] Skip  [q] Quit
```

| Key | Action |
|---|---|
| `a` | Accept the proposed match as-is |
| `e` | Edit individual fields before saving |
| `p` | Play the file, then return to the prompt |
| `s` | Skip this file (stays `no_match`) |
| `q` | Quit, resume later |

After the pass, run `--move` to tag and move the newly identified files:

```
python3 main.py --move
```

---

## Output folder structure

Organised files land in `Music/` using this pattern:

```
Music/<Language>/<Year>/<Album>/<Title>.mp3
```

Examples:

```
Music/Tamil/1987/Rettai Vaal Kuruvi.../Raja Raja Chozhan.mp3
Music/Hindi/1974/Roti Kapda Aur Makaan/Aaj Ki Raat.mp3
Music/English/1999/Issues/Evolution.mp3
```

**Duplicate songs** (same title+artist+language already exists in `Music/`) are automatically
routed to a `Duplicates/` folder for manual comparison:

```
Music/Tamil/Duplicates/Minnale/Vaseegara (max-000031).mp3
```

The original stays in its normal path. Open both files in a player, keep the
better-quality one, and delete the other.

Missing fields fall back gracefully:

```
No year  → Music/Tamil/Unknown Year/Minnale/Vaseegara.mp3
No album → Music/Tamil/2001/Unknown Album/Vaseegara.mp3
```

**Collection-fix songs** are files that Shazam could not identify but whose filename
contained a `from <Album>` clue (e.g. `Vaseegara (From Minnale).mp3`). These are
identified automatically and routed to a `Collections/` folder:

```
Music/Tamil/Collections/Minnale/Vaseegara.mp3
Music/Hindi/Collections/Muqaddar Ka Sikandar/O Saathi Re.mp3
```

If the year is later resolved (via manual review or a future identification pass), the
file will be re-routed to the standard year-based path.

Characters illegal in filenames (`/ \ : * ? " < > |`) are replaced with `_`.
All other characters — including Tamil script, Hindi script, parentheses, ampersands, and
hyphens — are preserved exactly.

---

## Full CLI reference

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
| `python3 main.py --review --folder PATH` | Review only songs whose path contains PATH |
| `python3 main.py --stats` | Print DB summary — no files touched |
| `python3 main.py --check` | Verify DB tables exist — nothing else |
| `python3 main.py --move` | Tag and move all identified songs to `Music/` (stages 3+4, no source needed) |
| `python3 main.py --move --dry-run` | Preview what `--move` would do without changing anything |
| `python3 main.py --metadata-search` | Search iTunes for `no_match` files using ID3 tags or filename |
| `python3 main.py --metadata-search --all` | Same but runs on every song regardless of status |
| `python3 main.py --metadata-search --folder PATH` | Limit metadata search to songs whose path contains PATH |
| `python3 main.py --acoustid` | AcoustID fallback pass: fingerprint no_match songs and review interactively |
| `python3 main.py --zeroise` | Clear all songs and runs from the database (asks for confirmation) |
| `streamlit run gui.py` | Launch read-only NL query GUI (requires `ANTHROPIC_API_KEY`) |

---

## Match rate expectations

Based on testing with a real collection:

| Music type | Expected match rate | Notes |
|---|---|---|
| Tamil film music 1990s–2010s | ~90% | Strong Shazam coverage |
| Tamil film music 1970s–1980s | ~75% | Good — Ilaiyaraaja era well indexed |
| Hindi film music (Bollywood) | ~85–90% | Excellent coverage |
| English mainstream | ~90%+ | Shazam's original strength |
| Obscure / regional / pre-1970 | ~40–60% | Falls back to manual review |
| Non-music (noise, speech) | 0% | Expected — use `--review` to tag manually |

**Main causes of `no_match`:**

1. Audio fingerprint not present in Shazam's database
2. File shorter than 8 seconds
3. Very obscure or locally-released recordings never submitted to Shazam

---

## Transliteration pass *(v1.2.0)*

The `--transliterate` pass converts the `Artist` ID3 tag for Tamil and Hindi songs from
Roman script to native script using Sarvam AI.

**Example:** `Ilaiyaraaja` → `இளையராஜா` (Tamil), `Lata Mangeshkar` → `लता मंगेशकर` (Hindi)

### Prerequisites

1. **Register** for a free account at [sarvam.ai](https://sarvam.ai) to get an API key.
   Docs: https://docs.sarvam.ai/api-reference-docs/text/transliterate-text

2. **Set the environment variable:**
   ```
   export SARVAM_API_KEY=your_key_here
   ```

### Running the pass

```
python3 main.py --transliterate
```

Each unique artist name per language is sent to Sarvam once and cached in the
`artist_transliterations` table in `music.db`. Subsequent runs and re-runs use the
cache — no repeat API calls.

**Notes:**
- Only `Artist` tag is affected — filenames and folder names are unchanged
- English songs are skipped entirely
- Compound artist strings (e.g. `A.R. Rahman & Lata Mangeshkar`) are split, each name
  transliterated independently, then reassembled
- The target script follows the song's language: Tamil songs → Tamil script, Hindi → Devanagari
- ~5–10% of songs may be mis-classified due to folder-based language detection; this is
  accepted noise and can be reviewed via the GUI

---

## GUI — natural language query tool *(v1.2.0)*

A lightweight local web UI that lets you query `music.db` in plain English.
Results are shown as a table with file paths. **Read-only — nothing is written or moved.**

### Prerequisites

1. **Claude API key** from [console.anthropic.com](https://console.anthropic.com):
   ```
   export ANTHROPIC_API_KEY=your_key_here
   ```

2. **Install extra dependencies** (inside your virtual environment if you're using one):
   ```
   pip install streamlit anthropic
   ```

3. **Verify Streamlit installed correctly:**
   ```
   streamlit --version
   ```
   If this returns `command not found`, your virtual environment is not activated — run
   `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows) first,
   then retry.

   > **Note:** Streamlit is a separate web framework that opens a local server in your
   > browser. It is not launched with `python3` — use `streamlit run` instead (see below).
   > Port 8501 is used by default. If something else is already on that port (e.g. another
   > Streamlit app), pass `--server.port 8502` to use a different one.

### Running the GUI

```
streamlit run gui.py
```

Streamlit will print a local URL — open it in your browser (default `http://localhost:8501`).
On Linux it will not auto-open the browser; copy the URL from the terminal output manually.

To use a different port:
```
streamlit run gui.py --server.port 8502
```

### Canned reports

Always available from the report menu — no typing needed:

- Songs flagged for review
- No-match songs by language
- Unknown Year queue
- Unknown Album queue
- Language breakdown summary
- Transliteration cache viewer

### Natural language queries

Type any question in plain English. Examples:

```
show me all Tamil songs from 1981
find everything by Ilaiyaraaja
show songs where the album is unknown
how many Hindi songs do I have
```

Results include the file path so you can navigate directly to the file.
For flagged songs, a suggested CLI command is shown to help you correct the issue.

### Who this is for

Sruthi is for anyone managing a large MP3 collection — particularly Tamil, Hindi, and other
South Asian music from the pre-streaming era — where standard tools give poor metadata
coverage. It is a command-line tool; basic terminal comfort is assumed. The GUI is an
optional read-only layer on top; it does not replace the CLI.

---

## Bugs and new features

**Found a bug?** Open an issue at:
```
https://github.com/fordevices/sruthi/issues
```
Label it `bug`. Include: OS, Python version, the command you ran, and the relevant lines
from `runs/<timestamp>/run.log`.

**Want a new feature?** Open an issue at the same URL.
Label it `enhancement`. Describe: what you want to do that you currently cannot.

**Common candidates for future issues:**

- Support for `.flac`, `.m4a`, `.ogg` files (not just `.mp3`)
- Lyrics fetching and USLT tag writing
- A simple web UI instead of the terminal review CLI
- Batch export of `music.db` to CSV or JSON
- AcoustID fallback auto-switch if ShazamIO stops working

> Do not raise issues for ShazamIO breaking due to Shazam API changes —
> that is an upstream dependency. See the "Fallback plan" section in README.md.

---

## Fallback if ShazamIO breaks

ShazamIO reverse-engineers Shazam's private API. If it ever stops working:

1. `pip install pyacoustid`
2. Install Chromaprint:
   - macOS: `brew install chromaprint`
   - Linux: `sudo apt install libchromaprint-tools`
   - Windows: download `fpcalc` from https://acoustid.org/chromaprint
3. Register a free API key at https://acoustid.org (2 minutes, no payment required)
4. Replace `pipeline/identify.py` with an AcoustID implementation

The database schema, all other stages, the review CLI, and the folder structure are
completely unchanged. Only Stage 1 needs to be swapped.

Match rate for Indian music will drop from ~86% to ~50–60% on older tracks.
