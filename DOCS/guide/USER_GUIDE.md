# Sruthi — User Guide

Sruthi takes a folder full of MP3 files — even ones with garbled names and missing information — and sorts them into a clean, properly labelled music library. It listens to each song, figures out what it is, fills in the correct song name, artist, album, and year, then moves it into a tidy folder structure like `Music/Hindi/1994/Hum Aapke Hain Koun/`.

It works especially well for Tamil and Hindi music from the 1970s–2000s, which most other tools miss.

> **Useful links:**
> [Architecture](ARCHITECTURE.md) — how it works under the hood |
> [Database reference](DATABASE.md) — what gets stored and why |
> [Music files primer](MUSIC_FILES_PRIMER.md) — what fingerprinting actually does

---

## Before you start

### What you need

| What | Version | How to check |
|---|---|---|
| Python | 3.10 or newer | `python3 --version` |
| Internet connection | Always on | Required for song identification |
| Disk space | At least as much as your music | The tool moves files, it does not copy them |

Everything else (the Python libraries) installs automatically in the next step.

**Optional extras** — only needed if you want specific features:

| Feature | What you need |
|---|---|
| Artist name transliteration (e.g. `Ilaiyaraaja` → `இளையராஜா`) | Free Sarvam AI API key — register at [sarvam.ai](https://sarvam.ai), then: `export SARVAM_API_KEY=your_key` |
| Natural language search GUI | Free Anthropic API key — [console.anthropic.com](https://console.anthropic.com), then: `export ANTHROPIC_API_KEY=your_key` |
| ACRCloud identification (best for pre-2000 Indian music) | Free ACRCloud account — [console.acrcloud.com](https://console.acrcloud.com), then set three keys (see [ACRCloud section](#2-acrcloud-pass--best-for-pre-2000-indian-music)) |

---

### Installation

**macOS**

```
brew install python
git clone https://github.com/fordevices/sruthi.git
cd sruthi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py --check
```

**Linux (Ubuntu / Debian)**

```
sudo apt update && sudo apt install python3 python3-pip python3-venv
git clone https://github.com/fordevices/sruthi.git
cd sruthi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py --check
```

**Windows**

Install Python 3.10+ from [python.org](https://python.org) — tick **"Add Python to PATH"** during install. Then open Command Prompt or PowerShell:

```
git clone https://github.com/fordevices/sruthi.git
cd sruthi
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py --check
```

> On Windows, use `python` instead of `python3` throughout this guide.
> Audio playback during `--review` is not available on Windows — open files in VLC or Windows Media Player instead.

If `--check` prints `DB OK`, you are ready to go.

---

## Your first run

### Step 1 — Sort your MP3s by language

Create language folders inside `Input/` and put your MP3s in them. Subfolders inside those are fine — Sruthi will find everything.

```
Input/
├── Tamil/
├── Hindi/
├── English/
└── Other/        ← use this for anything else (Malayalam, Telugu, etc.)
```

You do not need to rename anything. The filenames can be completely garbled — that is the whole point.

> **The folder name becomes the language label.** You can call them anything — `Malayalam`, `French`, `Oldies` — but be consistent. Whatever you name the folder is what appears in `Music/` and in the database.

---

### Step 2 — Run it

```
python3 main.py Input/
```

Sruthi will work through every file. You will see one line per song as it goes:

```
[max-000012] ✓ identified  (12/500) Hindi | Tujhe Dekha To — Kumar Sanu & Lata Mangeshkar
[max-000014] ✗ no match    (14/500) Hindi | 0047_track14.mp3
```

A green ✓ means the song was identified and moved to `Music/`. A red ✗ means Sruthi could not figure out what the song is — it will stay in `Input/` for now and you can deal with it separately (see [What to do with unmatched songs](#what-to-do-with-unmatched-songs) below).

**How long does it take?** About 2 seconds per song for the identification step. A collection of 1,000 songs takes roughly 30–35 minutes. You can stop at any time with Ctrl-C and run the same command again later — it will pick up exactly where it left off without re-processing songs already done.

---

### Step 3 — Check the results

```
python3 main.py --stats
```

This shows a breakdown of how many songs were identified, how many are still unmatched, and how many files are in your `Music/` folder. Nothing is changed when you run `--stats`.

---

### What your library looks like after a run

Identified songs land in `Music/` like this:

```
Music/
├── Hindi/
│   ├── 1994/
│   │   └── Hum Aapke Hain Koun/
│   │       ├── Didi Tera Dewar Deewana — Lata Mangeshkar & S.P. Balasubramaniam.mp3
│   │       └── Pehla Pehla Pyar Hai — Kumar Sanu & Kavita Krishnamurthy.mp3
│   └── Unknown Year/
│       └── ...
├── Tamil/
│   └── 1987/
│       └── ...
└── English/
    └── ...
```

If a field is missing, Sruthi falls back gracefully:

| Situation | Where it goes |
|---|---|
| Year unknown | `Music/Hindi/Unknown Year/Album/` |
| Album unknown | `Music/Hindi/1994/Unknown Album/` |
| Duplicate of a song already in your library | `Music/Hindi/Duplicates/Album/` |

> **Duplicates folder:** If the same song appears twice (e.g. original and a compilation re-release), Sruthi keeps one copy in the normal location and puts the other in `Duplicates/`. Open both in a music player, keep the better quality one, delete the other.

---

## What to do with unmatched songs

After your first run, some songs will still be in `Input/` with no match. Here is what to try, in order:

```
Not identified by Shazam?
        │
        ├─ Try multiprobe  →  python3 main.py --multiprobe
        │  (free, automatic, takes ~2s/song, gets 10–20% more matches)
        │
        ├─ Try ACRCloud   →  python3 main.py --acrcloud
        │  (free account, 1,000 songs/day, best for pre-2000 Indian music)
        │
        ├─ Try metadata search  →  python3 main.py --metadata-search
        │  (searches iTunes using existing tags or filename, interactive)
        │
        └─ Enter manually  →  python3 main.py --review
           (listen and type the details yourself, one song at a time)
```

After each pass, run `python3 main.py --move` to move the newly identified songs into `Music/`.

> **One at a time.** Never run two Sruthi commands simultaneously. They all write to the same database file and will conflict with each other. Wait for one to finish before starting the next.

---

### 1. Multiprobe pass — free, no account needed

Shazam sometimes misses a song if the loudest or most recognisable part happens to fall outside the section it sampled. Multiprobe tries four different points in each song instead of one.

```
python3 main.py --multiprobe
python3 main.py --move
```

No setup, no quota. Good first step.

---

### 2. ACRCloud pass — best for pre-2000 Indian music

ACRCloud has a different music database to Shazam — it includes the Saregama/HMV India catalogue, which is the biggest archive of older Tamil and Hindi film music. If you have a lot of 1970s–1990s Bollywood or Tamil classics that Shazam missed, ACRCloud will often get them.

**Free limit:** 1,000 songs per day. Quota resets at midnight UTC (7 pm US Eastern time).

**One-time setup:**

1. Create a free account at [console.acrcloud.com](https://console.acrcloud.com) — choose a "Recorded Music" project
2. Copy the three credentials from your project dashboard
3. Set them in your terminal (add to `~/.bashrc` to make permanent):

```
export ACRCLOUD_HOST=identify-ap-southeast-1.acrcloud.com
export ACRCLOUD_ACCESS_KEY=your_access_key
export ACRCLOUD_ACCESS_SECRET=your_access_secret
```

**Running it:**

```
python3 main.py --acrcloud
python3 main.py --move
```

If you have more than 1,000 unmatched songs, cap the run and do it over multiple days:

```
python3 main.py --acrcloud --limit 900    ← leaves a 100-song buffer before the daily limit
```

To run it on one language only:

```
python3 main.py --acrcloud --language Hindi
```

ACRCloud remembers which songs it already tried — re-running it will not waste your daily quota on songs it already attempted.

---

### 3. Metadata search — searches iTunes by song name

This pass reads whatever information is already in the file — existing tags or the filename itself — and searches iTunes for a match. It shows you up to three candidates and lets you pick the right one.

```
python3 main.py --metadata-search
python3 main.py --move
```

No account or API key required. Works best when the filename is somewhat meaningful (e.g. `Tujhe Dekha To - Kumar Sanu - DDLJ.mp3`).

For each song you will see something like:

```
────────────────────────────────────────────
File     : Input/Hindi/Tujhe Dekha To - Kumar Sanu.mp3
Search   : 'Tujhe Dekha To'
── Candidates ──
  [1]  Tujhe Dekha To — Kumar Sanu & Lata Mangeshkar  |  Dilwale Dulhania Le Jayenge  1995
  [2]  Tujhe Dekha To — Kumar Sanu  |  Best of 90s  2005
  [3]  Tujhe Dekha To (Remix) — DJ Suketu  |  Remix Album  2003
────────────────────────────────────────────
[1/2/3] Pick  [e] Edit manually  [p] Play  [s] Skip  [q] Quit
```

Press the number to pick a match, `s` to skip, or `e` to type the details yourself.

---

### 4. Manual review — last resort

For anything that still has not been identified, you can listen to each song and enter the details by hand.

```
python3 main.py --review
python3 main.py --move
```

For each song you will hear it play (macOS/Linux) and see whatever Sruthi knows about it. Press `e` to enter the details:

```
Title | Artist | Album | Year
```

Examples:

```
Tujhe Dekha To | Kumar Sanu, Lata Mangeshkar | DDLJ | 1995
Vaseegara | Bombay Jayashri | Minnale | 2001
```

You can leave fields blank to keep existing values:

```
| | | 1995    ← fixes only the year
```

Other review options:

```
python3 main.py --review --flagged    ← only shows songs with suspicious years (e.g. year 1905 — likely means 1995)
python3 main.py --review --limit 20  ← review only the next 20 songs, then stop
python3 main.py --review --all       ← review every song including ones already identified
```

---

## Keeping your library tidy

### After identifying songs — move them into Music/

Any identification pass (multiprobe, ACRCloud, metadata search, manual review) marks songs as ready to move but does not move them automatically. Run this when you are done identifying:

```
python3 main.py --move
```

You can run `--move` at any time — it will only touch songs that have been identified but not yet filed.

---

### Check library health

```
python3 main.py --stats
```

Shows how many songs are done, unmatched, or in error — broken down by language. Also shows how many files are on disk vs. what the database expects, so you can spot anything that is out of sync.

---

### When you delete files from Input/

If you decide to delete some unmatched songs from `Input/` manually (e.g. you do not want certain tracks), run this afterwards to update the database:

```
python3 main.py --mark-removed
```

This scans for unmatched songs whose files are no longer on disk and marks them as removed. Without this, they stay in the database as "unmatched" even though the file is gone.

---

### Preview before committing

Not sure what a command will do? Add `--dry-run`:

```
python3 main.py Input/ --dry-run
python3 main.py --move --dry-run
```

Nothing is written, moved, or changed. You just see what would happen.

---

## Optional features

### Artist name transliteration

Converts artist names from Roman script to native script in the song tags:

`Ilaiyaraaja` → `இளையராஜா` (Tamil)
`Lata Mangeshkar` → `लता मंगेशकर` (Hindi)

Requires a free Sarvam AI API key (set `SARVAM_API_KEY`). Each unique artist name is only sent once — subsequent runs use a local cache.

```
python3 main.py --transliterate --dry-run    ← preview first
python3 main.py --transliterate              ← apply
```

Only affects the Artist tag inside the MP3 file. Filenames and folder names are not changed. English songs are skipped entirely.

---

### Natural language search (GUI)

A browser-based interface where you can ask questions about your library in plain English:

```
show me all Tamil songs from 1981
find everything by Ilaiyaraaja
how many Hindi songs do I have
show songs where the year is unknown
```

Requires a free Anthropic API key (set `ANTHROPIC_API_KEY`) and two extra packages:

```
pip install streamlit anthropic
streamlit run gui.py
```

Then open the URL it prints (usually `http://localhost:8501`). Read-only — nothing in your library is changed.

---

## Full command reference

| Command | What it does |
|---|---|
| `python3 main.py Input/` | Identify, tag, and move everything in Input/ |
| `python3 main.py Input/Hindi/` | Same, but only the Hindi folder |
| `python3 main.py Input/ --dry-run` | Preview only — nothing written or moved |
| `python3 main.py Input/ --stage 1` | Identify only (no tagging or moving) |
| `python3 main.py --move` | Tag and move all identified songs |
| `python3 main.py --move --dry-run` | Preview what --move would do |
| `python3 main.py --stats` | Show library summary — nothing changed |
| `python3 main.py --check` | Verify the database is healthy |
| `python3 main.py --multiprobe` | Re-try unmatched songs at 4 different positions via Shazam |
| `python3 main.py --acrcloud` | ACRCloud identification pass (all unmatched songs) |
| `python3 main.py --acrcloud --language Hindi` | ACRCloud — Hindi only |
| `python3 main.py --acrcloud --limit 900` | ACRCloud — stop after 900 songs |
| `python3 main.py --metadata-search` | iTunes search pass — interactive |
| `python3 main.py --metadata-search --all` | Same but runs on already-identified songs too |
| `python3 main.py --review` | Manually review unmatched songs |
| `python3 main.py --review --flagged` | Review only songs with suspicious years |
| `python3 main.py --review --all` | Review every song including matched ones |
| `python3 main.py --review --limit N` | Review only the next N songs |
| `python3 main.py --retry-no-match Input/` | Re-run Shazam on all unmatched songs |
| `python3 main.py --mark-removed` | Mark unmatched songs whose files are gone from disk |
| `python3 main.py --transliterate` | Transliterate artist names to native script |
| `python3 main.py --transliterate --dry-run` | Preview transliterations |
| `python3 main.py --zeroise` | Wipe the database and start fresh (asks for confirmation) |
| `streamlit run gui.py` | Launch the natural language search GUI |

---

## What match rates to expect

| Music type | Shazam alone | With ACRCloud |
|---|---|---|
| Hindi film music 1985–2000 | 45–80% | 80–90% |
| Hindi film music 1950–1984 | 15–40% | 55–75% |
| Tamil film music 1990s–2010s | ~90% | ~95% |
| Tamil film music 1970s–1980s | ~75% | ~85% |
| English mainstream | 90%+ | — |
| Obscure / regional / pre-1970 | 40–60% | varies |

Songs that remain unmatched after all passes are usually:
- Very obscure or locally-released recordings never submitted to any database
- Files shorter than 8 seconds
- Corrupt or non-standard MP3 files

---

## Troubleshooting

**"database is locked" error**
You ran two Sruthi commands at the same time. Wait for the first one to finish before running another.

**Run stopped partway through**
Run the same command again. Sruthi will skip everything already processed and continue from where it left off.

**Song identified with the wrong year**
Run `python3 main.py --review --flagged` — this surfaces songs with implausible years (before 1940 or in the future) for you to correct. For other year errors, run `python3 main.py --review --all` and navigate to the song.

**ACRCloud says "quota exceeded"**
You have hit the 1,000/day free limit. Wait until midnight UTC (7 pm US Eastern) and run again. Use `--limit 900` to leave a buffer.

**A file ended up in Music/Duplicates/**
Sruthi found the same song already in your library. Open both copies, keep the better quality one, delete the other. The original stays in its normal location.

**Songs moved to Music/Unknown Year/**
Shazam or the other identification sources did not return a year for these songs. Run `python3 main.py --metadata-search --all --folder "Unknown Year"` to try filling in the gaps, or correct them via `--review --all`.

---

## Reporting bugs and requesting features

Open an issue at **https://github.com/fordevices/sruthi/issues**

For bugs, include: your OS, Python version, the command you ran, and the relevant lines from `runs/<timestamp>/run.log`.
