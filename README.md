# Sruthi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Identifies MP3s by audio fingerprint, repairs their ID3 tags, and organises
> them into a clean `Language/Year/Album/` folder tree.
> Built for large multilingual collections — Tamil, Hindi, English, and beyond.

Works on macOS, Linux, and Windows.

---

## What Sruthi does

Most music tools assume well-tagged files. Indian music collections rarely have
that luxury — garbled filenames, empty tags, wrong years, and albums that
MusicBrainz Picard has never heard of. Sruthi works the other way: it listens to
the audio, figures out what the song is, and fixes everything from there.

It uses three identification engines in sequence:

**Shazam (ShazamIO)**
The first and fastest pass. Sends a short audio fingerprint to Shazam's database
— no API key, no account, no cost. Identifies mainstream Tamil, Hindi, and English
music at 80–90% for most collections. Fills in title, artist, album, and year.

**ACRCloud**
The second pass, and the key one for Indian music. ACRCloud has formal catalog
licensing with Saregama (formerly HMV India), which holds the largest archive of
pre-2000 Indian film music. These tracks are simply absent from Shazam's database.
ACRCloud's free tier covers 1,000 queries per day; paid tiers remove that cap.
This is the step that turns a 20% match rate on older Tamil and Hindi songs into
something workable.

**iTunes metadata search**
The third pass. For anything neither fingerprinter recognises, Sruthi reads the
file's existing ID3 tags — title, artist — and searches the iTunes catalogue. If
the tags are empty it falls back to a cleaned version of the filename. You review
the top 3 candidates and pick the right one. No account or API key required.

**Organising and moving**
Once a song is identified, Sruthi writes its ID3 tags with Mutagen and moves the
file to:
```
Music/<Language>/<Year>/<Album>/<Title> - <Artist>.mp3
```
Duplicates (same audio hash, different file) go to `Music/Duplicates/` rather than
overwriting. Everything is tracked in a local SQLite database (`music.db`) so any
run can be stopped and resumed safely.

**Metrics**
```bash
python3 main.py --stats
```
Prints a language-by-status grid showing how many songs are done, still unmatched,
or errored — both in the database and on disk. Also shows the backlog split: how
many songs have never been tried with ACRCloud versus how many have been tried and
still didn't match.

---

## Walkthrough for a new user

### 1. Install

```bash
git clone https://github.com/fordevices/sruthi.git
cd sruthi
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py --check   # verify the database initialised correctly
```

### 2. Sort your MP3s by language and drop them in

Create language folders inside `Input/` and copy your files there. Filenames do
not matter — Sruthi identifies by listening to the audio, not by reading the name.

```
Input/
  Tamil/
  Hindi/
  English/
  Other/       ← anything else
```

If you have a mixed folder with no language labelling, put it in `Input/Other/`.
You can always move files between language folders and re-run.

### 3. Run the Shazam pass

```bash
python3 main.py Input/
```

This fingerprints every file and queries Shazam's database. For mainstream music
expect most files to be identified on the first run. Each matched file gets its
ID3 tags written and is moved to `Music/` immediately. When it finishes, check
where you stand:

```bash
python3 main.py --stats
```

You will see a table — done, no_match, error — broken down by language. The
no_match files are what Shazam could not identify. That is normal. Keep going.

### 4. Run the ACRCloud pass — required for Indian music

This is the most important step for Tamil and Hindi collections. The free ACRCloud
tier gives 1,000 queries per day, which is enough to work through a large backlog
over a few days. The paid tier removes the daily cap entirely.

**Get your credentials (free tier):**
1. Sign up at [console.acrcloud.com](https://console.acrcloud.com)
2. Create a new project — select **Recorded Music** as the project type
3. Copy your Host, Access Key, and Access Secret from the project dashboard

**Set them in your environment** (or add to a `.env` file in the project root):

```bash
export ACRCLOUD_HOST=identify-us-west-2.acrcloud.com   # use the host from your dashboard
export ACRCLOUD_ACCESS_KEY=your_access_key
export ACRCLOUD_ACCESS_SECRET=your_access_secret
```

**Run it — Tamil first, then Hindi:**

```bash
# Process all remaining Tamil no_match songs
python3 main.py --acrcloud --language Tamil

# Then Hindi — use --limit to stay within your daily quota
python3 main.py --acrcloud --language Hindi --limit 366
```

The free tier resets at midnight UTC (around 8pm US Eastern / 5:30am India).
Run it once before reset and once after to cover ~2,000 songs per calendar day.

After each ACRCloud run, move the newly identified files into `Music/`:

```bash
python3 main.py --move
```

Repeat until the Tamil and Hindi backlogs are exhausted.

### 5. Run the metadata search pass

For anything neither fingerprinter recognised, Sruthi searches iTunes using the
file's existing ID3 tags or cleaned filename. You review candidates interactively.

```bash
python3 main.py --metadata-search
```

Each file shows up to three iTunes matches. Press `1`, `2`, or `3` to accept a
match, `s` to skip, or `m` to type the metadata manually. When done:

```bash
python3 main.py --move
```

### 6. Review anything left manually

For files that no automated pass could identify:

```bash
python3 main.py --review
```

The tool shows you the filename and lets you type `Title | Artist | Album | Year`.
Press Enter to save, `s` to skip, `q` to quit. Run `--move` afterwards.

### 7. Optional — query your library in plain English

A local web UI lets you ask questions like "show me all Tamil songs from 1981" or
"find everything by Ilaiyaraaja" and see the results as a searchable table.
Read-only — nothing is moved or modified from the GUI.

Requires a Claude API key from [console.anthropic.com](https://console.anthropic.com).

```bash
export ANTHROPIC_API_KEY=your_key_here
streamlit run gui.py
```

Open the URL Streamlit prints (default `http://localhost:8501`). Type any question
in plain English — no SQL needed.

---

## After you're done

Every file you dropped into `Input/` has either been moved to `Music/` with full
ID3 tags, or is still in `Input/` and marked in the database as needing attention.
Run `--stats` at any time to see the full picture.

```bash
python3 main.py --stats
```

---

## Documentation

| Document | What it covers |
|---|---|
| [User Guide](DOCS/USER_GUIDE.md) | Full CLI reference, all flags, install on macOS / Linux / Windows |
| [Architecture](DOCS/ARCHITECTURE.md) | Pipeline stages, module layout, status flow, run logging |
| [Design Decisions](DOCS/DESIGN_DECISIONS.md) | Why these tools were chosen, API comparison, trade-offs |
| [Database Reference](DOCS/DATABASE.md) | Full schema, song ID format, interruption safety |
| [Batch Run History](DOCS/BATCH_RUN_HISTORY.md) | Record of every full batch run with summary stats |
| [Releases](DOCS/RELEASES.md) | Version history |
| [Contributing](CONTRIBUTING.md) | Bug reports, feature requests, PR workflow |
