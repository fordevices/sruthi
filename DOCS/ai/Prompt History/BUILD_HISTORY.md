# Build History

> How this codebase was built using Claude CLI across 7 sessions,
> with the real-world findings and decisions made at each step.

---

## Approach

The project was built using a README-as-source-of-truth approach. Before each session,
Claude CLI read `README.md` in full — every design decision, schema definition, and field
mapping was specified there before any code was written. After each session, the README was
updated with real findings from live API probing and actual test runs, so subsequent
sessions were grounded in observed behaviour rather than assumptions.

The key discipline: never write code that isn't derived from a spec, and never leave a
session without updating the spec with what was actually discovered.

---

## Sessions overview

| Session | What was built | Key finding |
|---|---|---|
| 0 | Design & planning — README, schema, session plan | Chose ShazamIO over AcoustID; decided language pre-sorting beats auto-detection |
| 1 | Scaffold: `config.py`, `db.py`, stub `main.py` | WAL mode is essential for resume-safety; `generate_song_id()` MAX+1 pattern established |
| 2 | Stage 1: `identify.py`, ShazamIO integration | `subtitle` is the artist field (not `artist`); 86% match rate on real Tamil/Hindi files |
| 3 | Stage 2: `review.py`, interactive review CLI | Shazam can return year `1905` for a 1995 film; partial override `\| \| \| 1995` fixed it |
| 4 | Stage 3: `tagger.py`, Mutagen ID3 write | Pre-existing `TXXX:Acoustid Id` frame was untouched — Mutagen writes only what you set |
| 5 | Stage 4: `organizer.py`, file rename + move | `:` in album names → `_`; `!` and `()` preserved; real cases confirmed the sanitize rules |
| 6 | Orchestrator: `runner.py`, run logging | Duplicate-handler guard needed in `setup_run_logging()` when called multiple times |
| 7 | Polish: colour output, short-file guard, `--stats` | `COALESCE(NULLIF(x,''), NULLIF(y,''), fallback)` needed to prevent empty-string row in top-albums |

---

## Session 1 — Scaffold + database layer

**What was built:** `requirements.txt`, `pipeline/__init__.py`, `pipeline/config.py`,
`pipeline/db.py`, stub `main.py`.

`db.py` established all eight database functions that every subsequent module depends on.
The WAL journal mode setting in `get_connection()` is what makes the pipeline
resume-safe — WAL allows readers to continue while a write is in progress, so a Ctrl-C
mid-run never corrupts the database.

**Verification:** `python3 main.py --check` returned:
```
Tables in music.db: ['runs', 'songs', 'sqlite_sequence']
DB OK
```

---

## Session 2 — ShazamIO identification

**What was built:** `pipeline/identify.py` — file walking, MD5 hashing, ShazamIO calls,
DB writes.

Before writing any parsing code, Claude CLI probed the live ShazamIO API against three
real files (one Tamil, one Hindi, one English) to discover the actual response structure.

### ShazamIO response parsing reference

The exact field paths used in `pipeline/identify.py`:

```python
# Title
title = out["track"]["title"]

# Artist — note: "subtitle", not "artist"
artist = out["track"]["subtitle"]

# Album and Year — walk sections looking for type="SONG", then metadata items
for section in out["track"].get("sections", []):
    if section.get("type") == "SONG":
        for item in section.get("metadata", []):
            if item.get("title") == "Album":
                album = item.get("text", "")
            if item.get("title") == "Released":
                year = item.get("text", "")

# Genre
genre = out["track"].get("genres", {}).get("primary", "")

# Cover art
cover_url = out["track"].get("images", {}).get("coverart", "")

# No match: track key absent
if not out.get("track"):
    # status = no_match
```

**Critical parsing note:** `out["track"]["releasedate"]` exists as `"DD-MM-YYYY"` — do
not use this. Use the `sections` metadata `Released` field instead; it returns just
`"YYYY"`, which is what the DB stores.

### Real-world findings — Session 2

Observed on 22 files (10 Tamil, 7 Hindi, 4 English + 1 no-match English):

| Observation | Example | Impact |
|---|---|---|
| Some tracks have **no album or year** in sections metadata | `max-000001` Fight the Power | Fields stored as `""` — handled correctly by empty-string default |
| Shazam DB can return **obviously wrong years** | `max-000015` Maharajanodu: `shazam_year="1905"` (film is from 1995) | Year warning (⚠) in review CLI is the main catch mechanism |
| 3 of 22 tracks (14%) returned **no_match** | KoRn-Evolution, two Tamil tracks | Manual review handles these |
| Match rate **86%** on 1970s–2000s Tamil/Hindi classics | — | Strong; Shazam well-indexed for this era |

---

## Session 3 — Manual review CLI

**What was built:** `pipeline/review.py` — interactive terminal UI for `no_match` files.

Two verification passes were run after building the review CLI:

**Pass 1 — KoRn-Evolution fix (full override):**
```
Enter: Title | Artist | Album | Year
> Evolution | KoRn | Issues | 1999
✓ Saved. Status → identified.
```

**Pass 2 — Maharajanodu year correction (partial override):**
```
Enter: Title | Artist | Album | Year
> | | | 1995
Parsed:
  Title  : (kept existing)
  Artist : (kept existing)
  Album  : (kept existing)
  Year   : 1995
✓ Saved.
```

The partial override syntax — leaving fields blank to keep existing values — was added
because of this exact case. Without it, correcting a single bad year would require
re-entering all four fields from memory.

**Real-world finding:** `--review --flagged` (year outside 1940–current) is the right
workflow after every large batch. The `1905` case is not unique — any Shazam DB entry
with a corrupted year will trigger it.

---

## Session 4 — Mutagen ID3 tagger

**What was built:** `pipeline/tagger.py` — writes all ID3 tags into each MP3 using Mutagen.

The `resolve()` field priority function:

```python
def resolve(final_val: str, shazam_val: str, fallback: str = "") -> str:
    if final_val and final_val.strip():
        return final_val.strip()
    if shazam_val and shazam_val.strip():
        return shazam_val.strip()
    return fallback
```

This function is also imported by `organizer.py` — both stages use the identical priority
logic, ensuring that a manual override in Stage 2 is honoured consistently through
Stages 3 and 4.

**Pass 3 verification — actual tag inspection:**

For `max-000001` Raja Raja Chozhan (Tamil, 1987):
```
TIT2=Raja Raja Chozhan
TPE1=Ilaiyaraaja, S. P. Balasubrahmanyam & Arunmozhi
TALB=Rettai Vaal Kuruvi (Original Motion Picture Soundtrack)
TDRC=1987
TCON=Tamil
TXXX:PIPELINE_ID=max-000001
APIC (cover art embedded)
```

For `max-000002` Evolution (English, 1999 — full manual override):
```
TIT2=Evolution
TPE1=KoRn
TALB=Issues
TDRC=1999
TXXX:PIPELINE_ID=max-000002
(no APIC — no cover URL for manual overrides)
```

**Real-world finding:** Pre-existing `TXXX:Acoustid Id` frames on files that had
previously been run through MusicBrainz Picard were untouched. Mutagen only writes
frames you explicitly set — it does not clear existing frames unless you delete them first.

---

## Session 5 — File organizer

**What was built:** `pipeline/organizer.py` — sanitize, path construction, file moves.

The `sanitize()` function:

```python
import re
_ILLEGAL = r'[/\\:*?"<>|]'

def sanitize(name: str) -> str:
    name = re.sub(_ILLEGAL, '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip(' .')
    return name or 'Unknown'
```

**Real-cases table** — verified against the 20 tagged songs:

| Song | Edge case | Expected output path |
|---|---|---|
| `max-000001` Fight the Power | `final_album=""`, `final_year=""` — both empty | `Music/English/Unknown Year/Unknown Album/Fight the Power.mp3` |
| `max-000002` Evolution | Full manual override, no cover URL | `Music/English/1999/Issues/Evolution.mp3` |
| `max-000015` Maharajanodu | Partial override: only year corrected (1905→1995) | `Music/Tamil/1995/Sathi Leelavathi (Original Motion Picture Soundtrack) - EP/Maharajanodu.mp3` |
| `max-000007` Chura Liya... | Title contains `"` (illegal) → replaced with `_` | `Music/Hindi/1973/Singing Icon - Asha Bhosle/Chura Liya Hai Tumne Jo Dil Ko (From _Yaadon Ki Baaraat_).mp3` |

**Other notable sanitizations from the real dataset:**

| Input | After sanitize() |
|---|---|
| `Word Up!: The Remixes - EP` | `Word Up!_ The Remixes - EP` (`:` → `_`) |
| `Kabhi Kabhie (Original Motion Picture Soundtrack) [Dialogues Version]` | unchanged — `()` and `[]` are legal |
| `Guru - Ullaasapparavaigal - Sikappu Rojakkal` | unchanged — hyphens legal |

**Real-world finding:** `Word Up!: The Remixes - EP` confirmed that `:` is sanitized to
`_` while `!` is preserved. This is the canonical test case for the boundary between
legal and illegal filename characters in this pipeline.

---

## Session 6 — Orchestrator + run logging

**What was built:** `pipeline/runner.py` — ties all stages together, ANSI colour constants,
duplicate-handler guard in `setup_run_logging()`, per-run `summary.json`.

**Pass 1 result** — 5 noise files (white/pink/brown noise) passed through Stage 1:
- All 5 correctly returned `no_match` (noise cannot be fingerprinted)
- Stages 3 and 4 were skipped (no `identified` rows to process)
- `runs/<timestamp>/summary.json` created correctly

**Pass 2 result** — `--stats` output after 25 total songs:
```
Status breakdown:
  done         20
  no_match      5
Language breakdown:
  Tamil        12
  Hindi         8
  English       5
```

**Key implementation detail:** `setup_run_logging()` requires a duplicate-handler guard.
Python's logging system accumulates handlers on a logger across calls within the same
process. Without the guard, running `--stage 1` then `--stage 3` in one invocation would
result in double-logging. The guard checks `if not logger.handlers` before adding new ones.

---

## Session 7 — Polish

**What was built:** Short-file guard in `identify.py`, ANSI colour constants in `runner.py`
(TTY-aware, suppressed when piped), `--stats` top-albums fix in `main.py`.

**Short-file guard** (files under 8 seconds skip ShazamIO):
```python
try:
    audio = MP3(file_path)
    duration = audio.info.length
except HeaderNotFoundError:
    duration = 999
if duration < 8.0:
    update_song(song_id, status="no_match",
                error_msg=f"too short for fingerprinting ({duration:.1f}s)")
    return _get_song_by_id(song_id)
```

**Top-albums SQL fix** — `COALESCE` with `NULLIF` on both shazam and final fields:
```sql
COALESCE(NULLIF(final_album,''), NULLIF(shazam_album,''), 'Unknown Album')
```
Without `NULLIF(shazam_album,'')`, songs with an empty `shazam_album` were showing as
a blank row in the top-albums table instead of falling back to `'Unknown Album'`.

**All five verification checks passed:**
1. Colour output: green/yellow/red visible in TTY, suppressed when piped to file
2. Short-file guard: 5-second test file → `no_match` without Shazam call
3. `--stats` top-albums: no empty-string row
4. 26th file (new real Tamil song): identified and moved correctly
5. `--review --flagged`: returned 0 results (all bad years already corrected)

---

## What the approach produced

- **26 files processed** across Tamil, Hindi, and English
- **86% automated match rate** (22 of 26 via ShazamIO, 4 no_match → 2 resolved via manual review)
- **0 pipeline errors** — every failure was caught, logged, and recovered from
- **7 modules** built across 7 sessions, each independently verifiable

**Two things that worked better than the original plan:**

1. **ShazamIO over AcoustID** — the 86% match rate on Tamil film music from the 1970s–2000s
   exceeded expectations. AcoustID's community database has gaps for this era that Shazam
   does not. The zero-setup advantage (no `fpcalc` binary) also proved significant.

2. **Partial override syntax** — `| | | 1995` to fix only one field without re-entering
   all four was not in the original design. It emerged from the Maharajanodu `1905` case
   in Session 3 and proved essential for `--review --flagged` workflow on bad Shazam years.

---

## Links

[README.md](../README.md) | [Architecture](ARCHITECTURE.md) | [Claude CLI Workflow](../CLAUDE_CLI_WORKFLOW.md)
