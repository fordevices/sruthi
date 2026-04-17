# Session Final — User Guide + Git Release
> Paste this entire prompt into Claude CLI from inside the project root directory.
> This is the last Claude CLI session. After this, all future work is a GitHub issue or PR.

---

```
Read README.md before doing anything — it is the source of truth for all content.

This is the final session. Two tasks:
  1. Create DOCS/USER_GUIDE.md — a complete guide for a third person to install and use this tool
  2. Initialise git, commit everything, tag v1.0.0, push to GitHub, create the release

Do not modify any pipeline/ code. Do not modify music.db. Touch only:
  - DOCS/USER_GUIDE.md  (create)
  - README.md           (two small additions described below)
  - git / GitHub        (init, commit, tag, push, release)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — CREATE DOCS/USER_GUIDE.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create the directory DOCS/ and write DOCS/USER_GUIDE.md with the following sections
in this exact order. Write for a third person who has never seen this project.
Use clear, plain language. No jargon beyond standard Python/terminal terms.

────────────────────────────────────────────
Section 1: Title + one-paragraph summary
────────────────────────────────────────────
# mp3-organizer-pipeline — User Guide

One paragraph: what the tool does, who it is for, what it produces.
Mention: Tamil, Hindi, English and other language MP3s; ShazamIO fingerprinting;
ID3 tagging; organised folder output; resume-safe for large collections.

────────────────────────────────────────────
Section 2: Requirements
────────────────────────────────────────────
## Requirements

Table with three columns: Item | Minimum version | Notes

Rows:
  Python        | 3.10+     | python3 --version to check
  pip           | any       | comes with Python
  shazamio      | 0.8+      | installed via pip
  mutagen       | any       | installed via pip
  requests      | any       | installed via pip
  Internet      | required  | ShazamIO sends audio to Shazam's servers
  Disk space    | ~50 MB    | for music.db + run logs; Music/ output varies

No API keys. No accounts. No system binaries beyond Python itself.

────────────────────────────────────────────
Section 3: Installation — macOS
────────────────────────────────────────────
## Installation

### macOS

Step-by-step with exact commands:

1. Install Python 3.10+ if not already installed
   Option A — Homebrew (recommended):
     brew install python
   Option B — Download installer from python.org

2. Clone the repo:
     git clone https://github.com/fordevices/mp3-organizer-pipeline.git
     cd mp3-organizer-pipeline

3. Create a virtual environment (recommended — keeps dependencies isolated):
     python3 -m venv venv
     source venv/bin/activate

4. Install dependencies:
     pip install -r requirements.txt

5. Verify:
     python3 main.py --check
   Expected output:
     Tables in music.db: ['runs', 'songs', 'sqlite_sequence']
     DB OK

────────────────────────────────────────────
Section 4: Installation — Linux (Ubuntu/Debian)
────────────────────────────────────────────
### Linux (Ubuntu / Debian)

1. Install Python 3.10+:
     sudo apt update
     sudo apt install python3 python3-pip python3-venv

2. Clone the repo:
     git clone https://github.com/fordevices/mp3-organizer-pipeline.git
     cd mp3-organizer-pipeline

3. Create a virtual environment:
     python3 -m venv venv
     source venv/bin/activate

4. Install dependencies:
     pip install -r requirements.txt

5. Verify:
     python3 main.py --check

────────────────────────────────────────────
Section 5: Installation — Windows
────────────────────────────────────────────
### Windows

Windows note: the pipeline runs on Windows but the audio playback feature in
--review mode uses afplay/mpg123 which are not available on Windows.
You can still use all other features; you just cannot play files during review.
Workaround: open the file in Windows Media Player or VLC separately while reviewing.

1. Install Python 3.10+ from python.org
   During install: check "Add Python to PATH"

2. Open Command Prompt or PowerShell, clone the repo:
     git clone https://github.com/fordevices/mp3-organizer-pipeline.git
     cd mp3-organizer-pipeline

3. Create a virtual environment:
     python -m venv venv
     venv\Scripts\activate

4. Install dependencies:
     pip install -r requirements.txt

5. Verify:
     python main.py --check

Note: all commands below use python3 — on Windows use python instead.

────────────────────────────────────────────
Section 6: First-time setup — sorting your files
────────────────────────────────────────────
## First-time setup

### Step 1 — Sort your MP3s by language

Before running the pipeline, create language subfolders inside Input/ and place
your MP3s there. Nested subfolders are fine — the pipeline walks recursively.

  Input/
  ├── Tamil/        ← Tamil songs (any filename, any subfolder depth)
  ├── Hindi/        ← Hindi songs
  ├── English/      ← English songs
  └── Other/        ← anything else

You do not need to rename files. The whole point of this tool is that the
filenames can be completely wrong or meaningless.

The folder name becomes the Language field in the database and in the output path.
You can use any folder name you like — Tamil, Hindi, English, Other, Malayalam,
Telugu, French — as long as it is consistent.

────────────────────────────────────────────
Section 7: Running the pipeline
────────────────────────────────────────────
## Running the pipeline

### Full run — process everything

  python3 main.py Input/

This runs all four stages in sequence:
  Stage 1 — Fingerprint each file with ShazamIO and look up metadata
  Stage 2 — (skipped in batch mode — see Manual Review below)
  Stage 3 — Write ID3 tags into each identified MP3
  Stage 4 — Rename and move each file to Music/<Language>/<Year>/<Album>/

Progress is printed live. Each file gets one line:
  [max-000012] ✓ identified  (12/47) Tamil | Raja Raja Chozhan — Ilaiyaraaja
  [max-000014] ✗ no match    (14/47) Tamil | Sathileelavathy_MarugoMarugo.mp3

A timestamped log folder is created automatically:
  runs/2026-03-21_14-32-00/
      run.log         full output for this run
      summary.json    machine-readable stats

### Process a single language folder

  python3 main.py Input/Tamil/

### Process a single file

  python3 main.py Input/Tamil/mystery_track.mp3

### Dry run — see what would happen without moving anything

  python3 main.py Input/ --dry-run

All four stages run in preview mode. No files are moved, no tags are written.
Useful before running on a large new batch.

### Run a specific stage only

  python3 main.py Input/ --stage 1    ← identify only
  python3 main.py Input/ --stage 3    ← tag only (identified songs)
  python3 main.py Input/ --stage 4    ← move only (tagged songs)

────────────────────────────────────────────
Section 8: Resuming an interrupted run
────────────────────────────────────────────
## Resuming an interrupted run

The pipeline is fully resume-safe. You can stop it at any time — Ctrl-C,
close the terminal window, or let it fail — and re-run the same command.

How it works:
- Every file is identified by its MD5 hash when first discovered
- Files already in the database with status=done are skipped instantly
- Files with status=error are retried
- Files with status=no_match wait for manual review (see below)

For a 1000-file collection at 2 seconds per Shazam call, a full run takes
roughly 33 minutes. You can run it overnight, interrupt halfway, and resume
the next day. Only the unprocessed files will be touched.

To check progress at any time without running anything:
  python3 main.py --stats

Output:
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

────────────────────────────────────────────
Section 9: Manual review — handling unmatched files
────────────────────────────────────────────
## Manual review

Some files will not be matched by ShazamIO — usually files with garbled
filenames where the audio fingerprint is not in Shazam's database, or files
that are too short, noisy, or corrupted.

These are saved with status=no_match and held until you review them.

### Review all unmatched files

  python3 main.py --review

For each file you will see:

  ────────────────────────────────────────────
  Song ID : max-000042
  File    : Input/Tamil/sattam_naanbaneyennathuuyir.mp3
  Language: Tamil
  Status  : no_match
  ── Shazam match ──
  Title   : (none)
  ────────────────────────────────────────────
  [p] Play  [s] Skip  [e] Edit metadata  [q] Quit

Options:
  p → plays the file in your terminal (macOS/Linux only)
  s → skip this file for now, come back later
  e → enter metadata manually
  q → quit review, resume later

### Entering metadata manually

Press e, then type in this format:
  Title | Artist | Album | Year

Examples:
  Vaseegara | Bombay Jayashri | Minnale | 2001
  Nadaan Parindey | Mohit Chauhan | Rockstar | 2011

You can leave fields blank to keep existing values:
  | | | 1995      ← fixes only the year, keeps title/artist/album

### Catch bad years from Shazam's own database

Shazam occasionally has wrong year data (e.g. 1905 instead of 1995).
Run this after every large batch to surface those:

  python3 main.py --review --flagged

Only shows songs where the year looks implausible (before 1940 or in the future).
Use the partial override  | | | 1995  to correct just the year.

### Other review modes

  python3 main.py --review --all        ← review every song, not just no_match
  python3 main.py --review --limit 20   ← review only the next 20 unmatched files

────────────────────────────────────────────
Section 10: Output folder structure
────────────────────────────────────────────
## Output folder structure

Organised files land in Music/ using this pattern:

  Music/<Language>/<Year>/<Album>/<Title>.mp3

Examples:
  Music/Tamil/1987/Rettai Vaal Kuruvi.../Raja Raja Chozhan.mp3
  Music/Hindi/1974/Roti Kapda Aur Makaan/Aaj Ki Raat.mp3
  Music/English/1999/Issues/Evolution.mp3

Missing fields fall back gracefully:
  No year  → Music/Tamil/Unknown Year/Minnale/Vaseegara.mp3
  No album → Music/Tamil/2001/Unknown Album/Vaseegara.mp3

Characters illegal in filenames ( / \ : * ? " < > | ) are replaced with _.
All other characters including Tamil script, Hindi script, parentheses,
ampersands, and hyphens are preserved exactly.

────────────────────────────────────────────
Section 11: Full CLI reference
────────────────────────────────────────────
## Full CLI reference

| Command | What it does |
|---|---|
| `python3 main.py Input/` | Full pipeline run on a folder (all stages) |
| `python3 main.py Input/ --dry-run` | Preview only — nothing written or moved |
| `python3 main.py Input/ --stage 1` | Identify only |
| `python3 main.py Input/ --stage 3` | Tag only (identified songs) |
| `python3 main.py Input/ --stage 4` | Move only (tagged songs) |
| `python3 main.py Input/ --review-after` | Run pipeline then drop into review |
| `python3 main.py --review` | Review all no_match files interactively |
| `python3 main.py --review --flagged` | Review only suspicious-year files |
| `python3 main.py --review --all` | Review every file including matched ones |
| `python3 main.py --review --limit N` | Review only next N unmatched files |
| `python3 main.py --stats` | Print DB summary — no files touched |
| `python3 main.py --check` | Verify DB tables exist — nothing else |

────────────────────────────────────────────
Section 12: match rate expectations
────────────────────────────────────────────
## Match rate expectations

Based on testing with a real collection:

| Music type | Expected match rate | Notes |
|---|---|---|
| Tamil film music 1990s–2010s | ~90% | Strong Shazam coverage |
| Tamil film music 1970s–1980s | ~75% | Good — Ilaiyaraaja era well indexed |
| Hindi film music (Bollywood) | ~85–90% | Excellent coverage |
| English mainstream | ~90%+ | Shazam's original strength |
| Obscure / regional / pre-1970 | ~40–60% | Falls back to manual review |
| Non-music (noise, speech) | 0% | Expected — use --review to tag manually |

The main causes of no_match:
1. Garbled romanised filenames with no existing fingerprint in Shazam's DB
2. Files shorter than 8 seconds
3. Very obscure or locally-released recordings never submitted to Shazam

────────────────────────────────────────────
Section 13: Bugs and new features
────────────────────────────────────────────
## Bugs and new features

This tool is at v1.0.0. The pipeline is complete and working.

**Found a bug?** Open an issue at:
  https://github.com/fordevices/mp3-organizer-pipeline/issues
  Label it `bug`. Include: OS, Python version, the command you ran,
  and the relevant lines from runs/<timestamp>/run.log.

**Want a new feature?** Open an issue at the same URL.
  Label it `enhancement`. Describe: what you want to do that you can't do now.

**Common candidates for future issues:**
  - Support for .flac, .m4a, .ogg files (not just .mp3)
  - Lyrics fetching and USLT tag writing
  - A simple web UI instead of the terminal review CLI
  - Batch export of music.db to CSV or JSON
  - AcoustID fallback auto-switch if ShazamIO stops working

Do not raise issues for ShazamIO breaking due to Shazam API changes —
that is an upstream dependency. See the "Fallback plan" section in README.md.

────────────────────────────────────────────
Section 14: Fallback if ShazamIO breaks
────────────────────────────────────────────
## Fallback if ShazamIO breaks

ShazamIO reverse-engineers Shazam's private API. If it ever stops working:

1. pip install pyacoustid
2. macOS:  brew install chromaprint
   Linux:  sudo apt install libchromaprint-tools
   Windows: download fpcalc from https://acoustid.org/chromaprint
3. Register a free API key at https://acoustid.org (2 minutes, no payment)
4. Replace pipeline/identify.py with an AcoustID implementation

The database schema, all other stages, the review CLI, and the folder structure
are completely unchanged. Only Stage 1 needs to be swapped.
Match rate for Indian music will drop from ~86% to ~50–60% on older tracks.

────────────────────────────────────────────
End of DOCS/USER_GUIDE.md
────────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — README.md ADDITIONS (two only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make exactly these two additions to README.md and nothing else:

Addition A — add this line immediately after the project completion line
(the line that reads "> **Project completed: March 21, 2026**"):

  > **Repository:** https://github.com/fordevices/mp3-organizer-pipeline
  > **User guide:** [DOCS/USER_GUIDE.md](DOCS/USER_GUIDE.md)

Addition B — add this section immediately before the "Fallback plan" section
at the bottom of README.md:

  ## Persistence and interruption safety

  `music.db` is a file on disk. It is never wiped, never reset, and never
  touched by closing a terminal window or Ctrl-C. It accumulates permanently
  across every run, every session, and every restart.

  | Interruption | What happens | Recovery |
  |---|---|---|
  | Ctrl-C mid-Stage 1 | Files before interruption are `done` or `no_match` in DB | Re-run — processed files skipped by MD5 hash |
  | Ctrl-C mid-Stage 3 | Interrupted file stays `identified` — tag may be partial | Re-run `--stage 3` — file is re-tagged cleanly |
  | Ctrl-C mid-Stage 4 | Interrupted file stays `tagged` — file may or may not have moved | Re-run `--stage 4` — move is retried |
  | Terminal closed | Identical to Ctrl-C — DB is not affected | Re-run same command |
  | `error` status | Stage failed for this file | Automatically retried on next run |
  | `no_match` status | Shazam could not identify file | Held until `--review` |

  For a 1000-file collection at the default 2-second sleep, a full Stage 1 run
  takes ~33 minutes. You can run it overnight, interrupt at any point, and resume
  the next day. Only unprocessed files are touched.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — GIT INITIALISATION AND RELEASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run these steps in order. Stop and report if any step fails.

Step 1 — Create .gitignore
Write a .gitignore file with these entries:

  # Python
  __pycache__/
  *.pyc
  *.pyo
  .python-version
  venv/
  .venv/
  env/

  # Pipeline runtime files — do NOT commit
  music.db
  music.db-wal
  music.db-shm
  runs/
  Music/
  Input/

  # OS
  .DS_Store
  Thumbs.db
  desktop.ini

  # Editor
  .vscode/
  .idea/
  *.swp

Explanation of what is and is not committed:
  COMMITTED:   All pipeline/ code, main.py, requirements.txt, README.md,
               DOCS/USER_GUIDE.md, .gitignore
  NOT COMMITTED: music.db (personal data), Music/ (organised output),
               Input/ (source files), runs/ (local logs)

Step 2 — Initialise git and make the first commit
  git init
  git add .
  git commit -m "feat: initial release v1.0.0

  Four-stage MP3 organization pipeline:
  - Stage 1: ShazamIO audio fingerprinting + identification
  - Stage 2: Interactive manual review CLI with partial overrides
  - Stage 3: Mutagen ID3 tag writing with field priority (final > shazam)
  - Stage 4: File organization to Music/Language/Year/Album/ structure

  Features:
  - Resume-safe via SQLite (music.db) with MD5 deduplication
  - Short-file guard (<8s skipped before Shazam call)
  - Year anomaly flagging (--review --flagged)
  - ANSI colour output, suppressed when piped
  - Per-run timestamped logs + summary.json
  - Dry-run mode for all stages
  - Full --stats DB summary without touching files

  Tested: 26 files, 86% match rate, Tamil/Hindi/English
  Python 3.10+ | shazamio | mutagen | requests | no API keys required"

Step 3 — Tag v1.0.0
  git tag -a v1.0.0 -m "v1.0.0 — initial release

  Complete, working pipeline. All 7 build sessions verified.
  See DOCS/USER_GUIDE.md for installation and usage instructions.
  See README.md for architecture, schema, and design decisions."

Step 4 — Add the GitHub remote and push
  git remote add origin https://github.com/fordevices/mp3-organizer-pipeline.git
  git branch -M main
  git push -u origin main
  git push origin v1.0.0

  If the push fails with authentication error: GitHub now requires a Personal
  Access Token (PAT) instead of a password. Generate one at:
    https://github.com/settings/tokens
  Select: repo scope. Use the token as the password when prompted.
  Alternatively set up SSH keys and use the SSH remote URL.

Step 5 — Create the GitHub release via gh CLI (if installed)
  gh release create v1.0.0 \
    --title "v1.0.0 — Initial Release" \
    --notes "## mp3-organizer-pipeline v1.0.0

  Transform a library of mystery MP3s into a perfectly organized, fully tagged collection.

  ### What's included
  - Four-stage pipeline: fingerprint → review → tag → organize
  - ShazamIO identification (no API key required)
  - Resume-safe for collections of any size via SQLite
  - Interactive manual review CLI for unmatched files
  - ANSI colour output, dry-run mode, per-run logs

  ### Match rate (tested)
  - Tamil film music 1970s–2010s: ~75–90%
  - Hindi film music: ~85–90%
  - English mainstream: ~90%+

  ### Installation
  \`\`\`bash
  git clone https://github.com/fordevices/mp3-organizer-pipeline.git
  cd mp3-organizer-pipeline
  python3 -m venv venv && source venv/bin/activate
  pip install -r requirements.txt
  python3 main.py --check
  \`\`\`

  See [DOCS/USER_GUIDE.md](DOCS/USER_GUIDE.md) for full installation and usage instructions.

  ### Requirements
  Python 3.10+ · No API keys · No system binaries · macOS / Linux / Windows"

  If gh is not installed, create the release manually on GitHub:
    1. Go to https://github.com/fordevices/mp3-organizer-pipeline/releases/new
    2. Choose tag: v1.0.0
    3. Title: v1.0.0 — Initial Release
    4. Copy the --notes content above into the description box
    5. Click "Publish release"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After all steps complete, confirm:

1. DOCS/USER_GUIDE.md exists and has all 14 sections
   wc -l DOCS/USER_GUIDE.md
   (expect 250+ lines)

2. README.md has the two additions
   grep -n "fordevices" README.md
   grep -n "Persistence and interruption" README.md
   (both should return line numbers)

3. .gitignore is correct
   cat .gitignore | grep "music.db"
   (should return: music.db)

4. git log is clean
   git log --oneline
   (should show exactly one commit)

5. Tag exists
   git tag
   (should show: v1.0.0)

6. Remote is set
   git remote -v
   (should show origin pointing to github.com/fordevices/mp3-organizer-pipeline)

Paste the output of all six verification commands.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER THIS SESSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This project is now at v1.0.0. The pipeline is complete.

Any future work — fixes, features, improvements — goes through GitHub:
  https://github.com/fordevices/mp3-organizer-pipeline/issues

Do NOT use Claude CLI for further development without first opening a GitHub issue
to define the scope. Each issue should be a self-contained, independently testable
change to one module. Use the existing session structure as the model:
  - Start with: "Read README.md before writing any code"
  - End with: a verification command whose output can be pasted to confirm it worked
  - Update README.md if any schema, CLI flags, or behaviour changes

The README.md and DOCS/USER_GUIDE.md are the source of truth.
Keep them updated with every change.
```
