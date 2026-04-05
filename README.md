# 🎵 Sruthi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Open-source MP3 library tool that identifies songs by audio fingerprint, repairs and
> enriches ID3 metadata from ShazamIO, MusicBrainz, and iTunes, then organises files
> into a clean `Language/Year/Album/` folder tree. Built for large multilingual collections
> — Tamil, Hindi, English, and beyond. Core pipeline runs with no API keys.
> Optional features (transliteration, NL query GUI) use Sarvam AI and Claude API.

Works on macOS, Linux, and Windows.

---

## From a pile of files to a clean library

If you have a large MP3 collection — Tamil classics, old Bollywood tracks, English songs — where the filenames are garbled (`track01.mp3`, `sattam_naanbaneyennathuuyir.mp3`), the ID3 tags are wrong or empty, and standard tools like beets or MusicBrainz Picard give poor results on Indian music, Sruthi is built for that problem.

It identifies songs by audio fingerprint via ShazamIO, fills in title, artist, album, and year, then moves each file to the right place. For anything Shazam misses, it searches MusicBrainz and iTunes using existing tags or the cleaned filename. What cannot be identified automatically goes to a manual review queue. Here is how it works.

**1. Sort by language, drop them in.**
Create language folders inside `Input/` and copy your files there. Filenames don't matter at all — that's the whole point.
```
Input/Tamil/    Input/Hindi/    Input/English/    Input/Other/
```

**2. Run it. Shazam identifies most files automatically.**
```bash
python3 main.py Input/
```
Sruthi sends a short audio fingerprint of each file to Shazam's database. No API key needed. For mainstream Tamil, Hindi, and English music expect 80–90% of files to be matched instantly — title, artist, album, year all filled in. Each matched file gets its ID3 tags written and is moved to `Music/<Language>/<Year>/<Album>/` in one pass.

**3. Some files won't match. That's normal.**
Recordings not in Shazam's database, older tracks, or live versions get saved as `no_match` and held for the next steps. Run `python3 main.py --stats` to see how many there are.

**4. Try the metadata search pass — no sign-up needed.**
Sruthi reads each file's existing ID3 tags (title, artist) first, falls back to the cleaned filename if tags are empty, and searches both MusicBrainz and iTunes with the best signal available:
```bash
python3 main.py --metadata-search
```
For each file you see up to 6 candidates (3 from MusicBrainz, 3 from iTunes) and pick the right one. No account or API key required. This resolves a large chunk of what Shazam missed.

**5. Optionally, try the AcoustID pass — deeper fingerprinting, free API key.**
AcoustID uses a different audio fingerprint algorithm that catches many songs Shazam misses. It requires a free API key from [acoustid.org](https://acoustid.org) (under 2 minutes to register) and the `fpcalc` binary:
```bash
export ACOUSTID_API_KEY=your_key_here
python3 main.py --acoustid
```
You can skip this step entirely if you'd rather not register — go straight to manual review instead.

**6. For everything left, type the metadata yourself.**
```bash
python3 main.py --review
```
The tool plays each file and lets you type `Title | Artist | Album | Year`. Skip any file you want to come back to later.

**7. Move everything that's now identified.**
After any of the steps above identify new files, run:
```bash
python3 main.py --move
```
This writes the ID3 tags and moves all newly identified files into `Music/` — the same organised folder structure as the original run.

**8. Optional — go back and correct already-identified files.**
Once the main run is done you may spot files that were identified correctly by Shazam but have a wrong year, different album version, or a better match available. Run the metadata search against everything — not just `no_match` files — and correct as you go:
```bash
python3 main.py --metadata-search --all
# optionally limit to one language folder:
python3 main.py --metadata-search --all --folder Tamil
```
After making corrections, run `--move` again to rewrite the tags and relocate any files whose metadata changed:
```bash
python3 main.py --move
```
Both steps are entirely optional — they're for tidying up after the main work is done.

**9. Optional — transliterate artist names to native script.**
Tamil and Hindi artist names returned by Shazam are always in Roman script (e.g.
`Ilaiyaraaja`, `Lata Mangeshkar`). This pass converts the `Artist` ID3 tag to native
script (Tamil or Devanagari) using Sarvam AI. Requires a free Sarvam API key from
[sarvam.ai](https://sarvam.ai). Each unique artist name is translated once and cached —
a name appearing in 200 songs costs one API call.
```bash
export SARVAM_API_KEY=your_key_here
python3 main.py --transliterate
```

**10. Optional — query your library in plain English.**
A lightweight local web UI lets you ask questions like "show me all Tamil songs from 1981"
or "find everything flagged for review" and see the results as a table with file paths.
Read-only — nothing is written or moved from the GUI. Requires a Claude API key.
```bash
export ANTHROPIC_API_KEY=your_key_here
streamlit run gui.py
```
Streamlit prints a local URL — open it in your browser (default `http://localhost:8501`).
Use the built-in report menu or type any question in plain English. No SQL knowledge needed.

When you're done, every file you dropped into `Input/` has either been organised into `Music/` with full tags, or is still sitting in `Input/` clearly marked in the database as needing attention.

---

## How it works

Each MP3 passes through four stages:

```
Input/Tamil/mystery_track.mp3
        │
        ▼
┌──────────────────────────────────────────────────┐
│  Stage 1 — ShazamIO audio fingerprint + identify │
│  Stage 2 — Manual review queue (no_match files)  │
│  Stage 3 — Mutagen writes ID3 tags into file     │
│  Stage 4 — File renamed and moved to folder      │
└──────────────────────────────────────────────────┘
        │
        ▼
Music/Tamil/2001/Minnale/Vaseegara.mp3
```

Every file is tracked in a local SQLite database (`music.db`). The pipeline is fully
resume-safe — stop it at any point, re-run the same command, and only unprocessed
files are touched. Safe to run on collections of tens of thousands of files.

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/fordevices/sruthi.git
cd sruthi
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py --check
```

```
# 2. Sort your files by language and drop them in
Input/Tamil/   Input/Hindi/   Input/English/   Input/Other/
```

```bash
# 3. Run
python3 main.py Input/
```

For full installation instructions including Windows, see [DOCS/USER_GUIDE.md](DOCS/USER_GUIDE.md).

---

## Documentation

| Document | What it covers |
|---|---|
| [User Guide](DOCS/USER_GUIDE.md) | Install on macOS / Linux / Windows, full CLI reference, running the Sruthi MP3 Pipeline, manual review, match rate expectations |
| [Architecture](DOCS/ARCHITECTURE.md) | Sruthi MP3 Pipeline stages, modules, file structure, status flow, run logging |
| [Design Decisions](DOCS/DESIGN_DECISIONS.md) | Why ShazamIO was chosen, API comparison table, trade-offs, fallback plan |
| [Database Reference](DOCS/DATABASE.md) | Full schema, song ID format, persistence, interruption safety |
| [Music Files Primer](DOCS/MUSIC_FILES_PRIMER.md) | What MP3s are, how ID3 tags work, what audio fingerprinting does, how Shazam works |
| [Run Statistics](DOCS/RUN_STATISTICS.md) | Results from the 5,550-file batch run — match rates by language, errors, observations |
| [Batch Run History](DOCS/BATCH_RUN_HISTORY.md) | Record of every full batch run with summary stats |
| [Releases](DOCS/RELEASES.md) | Version history — what shipped in each release, issues fixed |
| [System Testing](DOCS/SYSTEM_TESTING.md) | End-to-end test cases covering the full pipeline |
| [Regression Checklist](DOCS/REGRESSION_CHECKLIST.md) | Manual regression checklist to run before each release |
| [Contributing](CONTRIBUTING.md) | How to raise bugs and features, PR workflow, issue templates |
| [Claude CLI Workflow](CLAUDE_CLI_WORKFLOW.md) | How to use Claude CLI to implement issues on this repo |

---

## Results

Tested on a 5,550-file library (Tamil, Hindi, English): **68% automated match rate**, 3,768 files identified and moved, 1,700 no-match held for review, 4 errors. Run time: 5h 59m.

Full statistics: [DOCS/RUN_STATISTICS.md](DOCS/RUN_STATISTICS.md) · Release notes: [DOCS/RELEASES.md](DOCS/RELEASES.md)
