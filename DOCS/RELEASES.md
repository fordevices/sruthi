# Sruthi — Release Notes

Issues and feature requests: https://github.com/fordevices/sruthi/issues
Label bugs `bug`, feature requests `enhancement`.

---

## v1.3.0 *(in development)*

### New features

**Multi-probe Shazam pass** (`--multiprobe`, issue #32)
Re-attempts Shazam identification on `no_match` songs by probing at four time
positions within each file (15%, 35%, 55%, 75% of duration). For each probe,
a 15-second WAV slice is extracted via pydub and passed to `shazam.recognize(bytes)`.
The pass stops at the first hit and writes `id_source='shazam-multiprobe'`.

**Why it works:** ShazamIO's default probe sends a single window starting at the
song's midpoint. Older Tamil and Hindi film music often has 30–60 second orchestral
intros — the chorus (the indexed section) falls outside that window. The phone
Shazam app recognises these tracks because it listens to whatever the user plays,
which is typically the chorus. Multi-probe replicates that coverage automatically.

Run `--move` after `--multiprobe` to tag and file newly identified songs.

### New features (continued)

**ACRCloud fingerprint pass** (`--acrcloud`, issue #33)
Second fingerprint database targeting pre-2000 Tamil and Hindi film music.
ACRCloud has formal licensing deals with Saregama (HMV India), whose catalog
covers the exact gap Shazam misses. Single probe per song at 35% of duration.
Free tier: 1,000 queries/day (resets midnight UTC = 7pm US Eastern). Use
`--limit N` to manage quota across runs; default is 900. Fully automated.

Recommended sequence after a batch run:
```
python3 main.py --multiprobe       # unlimited, recovers wrong-window Shazam misses
python3 main.py --acrcloud         # 900/run, hits Saregama catalog Shazam can't reach
python3 main.py --move             # file everything identified
```

Setup: `pip install pyacrcloud` + three env vars from https://console.acrcloud.com

### Issues closed
\#32 (multi-probe Shazam pass), #33 (ACRCloud pass)

---

## v1.2.0 *(in development)*

### New features

**Transliteration pass** (`--transliterate`)
Converts the `Artist` ID3 tag for Tamil and Hindi songs from Roman script to native script
using Sarvam AI. Artist names are transliterated once per unique name per language and
cached in a new `artist_transliterations` table in `music.db` — a name appearing in 200
songs costs one API call. Requires a free Sarvam API key.

Example: `Ilaiyaraaja` → `இளையராஜா` (Tamil), `Lata Mangeshkar` → `लता मंगेशकर` (Hindi)

**Read-only query GUI** (`streamlit run gui.py`)
A lightweight local web UI that lets you query `music.db` in plain English. Type a question,
get a table. Includes built-in reports for common queries (flagged songs, no-match by
language, unknown year/album queues, transliteration cache). Read-only — never writes to
the database or touches files. Requires a Claude API key and `pip install streamlit anthropic`.

### Open issues
- #25 — song-level language detection (planned for a future release; current detection is
  folder-based, which misclassifies ~5–10% of songs in mixed-language collections)

### Issues closed
\#26 (transliteration pass), #27 (read-only GUI)

---

## v1.1.0 — April 3, 2026

### New features

**iTunes added to metadata search**
The `--metadata-search` pass now queries iTunes, showing up to 3 candidates per file.
iTunes has strong coverage of commercial Bollywood and Tamil film music.

**ID3 tag priority in metadata search**
Search queries now read existing ID3 tags (title, artist) from the file first, falling
back to the cleaned filename only when tags are absent. This significantly improves
candidate quality for files that were partially tagged.

**`--all` flag**
Pass `--metadata-search --all` to run the metadata search across every song in the
database, not just `no_match` files. Useful for correcting wrong years or album names
on files that Shazam already identified.

**`--folder` flag**
Scope any identification or review pass to a specific subfolder path. Useful for
working through one language or album at a time on large collections.

### Batch run results
Tested on 5,550 files: **68% automated match rate** — 3,768 identified and moved,
1,700 no_match held for review, 4 errors. Run time: 5h 59m.
See [RUN_STATISTICS.md](RUN_STATISTICS.md) for the full breakdown.

### Issues closed
\#7, #11, #13, #15, #16, #17, #18, #19, #22

---

## v1.0.0 — March 2026

Initial release.

### Features

**Four-stage pipeline**
- Stage 1 — ShazamIO audio fingerprint: identifies title, artist, album, year with no API key
- Stage 2 — Manual review CLI: plays each unmatched file, accepts typed metadata in `Title | Artist | Album | Year` format
- Stage 3 — Mutagen ID3 tag writer: writes all metadata into the file
- Stage 4 — File organiser: renames and moves to `Music/<Language>/<Year>/<Album>/`

**Resume-safe SQLite tracking**
Every file is recorded by MD5 hash in `music.db`. Re-running the same command skips
files already at `status=done`. Safe to interrupt and restart on collections of any size.

**AcoustID fallback pass** (`--acoustid`)
Secondary audio fingerprinting pass using the open AcoustID database.
Catches songs that Shazam cannot identify. Requires `fpcalc` (Chromaprint) and a free
AcoustID API key.

**Utilities**
`--dry-run`, `--stats`, `--check`, `--zeroise`, `--review --flagged`, `--move`
