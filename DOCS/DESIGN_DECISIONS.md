# Design Decisions

## The problem

A collection of 1000+ Tamil, Hindi, and English MP3 files with garbled filenames, missing
or wrong ID3 tags, and no consistent naming convention. Existing tools (MusicBrainz Picard,
beets, mp3tag) either require manual matching or rely on AcoustID — which has poor coverage
of Indian film music pre-2000. The goal was a zero-configuration pipeline that could handle
the entire collection overnight, with a review step for anything it couldn't identify
automatically.

---

## Key decisions

| Decision | Choice | Reason |
|---|---|---|
| Fingerprint engine | ShazamIO | Largest database, best Indian music coverage, no key, no binary required |
| Language classification | User pre-sorts input folders | Zero guesswork, full control, no language detection code needed |
| Output structure | `Language/Year/Album/` | Clean, chronological per language, mirrors how people browse music |
| Persistence | SQLite | Resume-safe, zero setup, single file, no server needed |
| Tagging library | Mutagen | Battle-tested ID3 writer, UTF-8 support, handles missing headers |

---

## Fingerprinting API comparison

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

---

## Why ShazamIO wins for this use case

- Shazam is the dominant music recognition app in India — Tamil and Hindi film music from the
  1970s onward is heavily indexed because millions of Indian users have Shazamed those songs.
- No `fpcalc` binary to install. No API key to register. Just `pip install shazamio` and go.
- The metadata package is richer out of the box — cover art URL is included in the response,
  no separate Cover Art Archive call needed.
- The library has been actively maintained for 4+ years through multiple Shazam API changes,
  which is a reasonable signal of durability for a personal project.

---

## Honest trade-off

ShazamIO reverse-engineers Shazam's private API. It is not an officially supported
integration. It could break if Apple/Shazam changes their internal endpoints. The library
has survived multiple such changes since 2021 (it is on v0.8.1 as of Jun 2025), but this
remains a real risk for a long-running project.

If it breaks, the fallback plan is AcoustID + MusicBrainz — fully documented below.

---

## Fallback plan — if ShazamIO breaks

1. `pip install pyacoustid`
2. Install Chromaprint:
   - macOS: `brew install chromaprint`
   - Linux: `sudo apt install libchromaprint-tools`
   - Windows: download `fpcalc` from https://acoustid.org/chromaprint
3. Register a free API key at https://acoustid.org (takes 2 minutes, no payment)
4. Replace `pipeline/identify.py` with an AcoustID implementation

The DB schema, all other stages, the review CLI, and the folder structure are completely
unchanged. Only Stage 1 needs to be swapped.

Match rate for Indian music will drop from ~86% to an estimated 40–70% on older tracks,
as AcoustID's community database has fewer Indian music submissions than Shazam's.

---

## Metadata search pass — design rationale

The `--metadata-search` pass (`pipeline/filename_pass.py`) is a text-based identification
pass for files that Shazam and AcoustID both failed on. It is distinct from audio
fingerprinting: rather than analysing the sound, it constructs a text query from whatever
signals are available and searches music metadata APIs.

### Signal priority

Many badly-named files have perfectly good ID3 tags embedded — the filename was garbled
by the ripper or download tool but the tags were set correctly at rip time. The pass
reads ID3 tags from the file before falling back to the cleaned filename:

1. **`TIT2` (title) + `TPE1` (artist)** — most precise; used when both are present
2. **`TIT2` (title) alone** — used when the artist tag is missing or empty
3. **Cleaned filename** — last resort; strips track numbers, underscores, brackets,
   year tokens, and square-bracket content before searching

### Query cascade

Rather than sending one query and giving up, the pass tries progressively simpler queries
until a result above a confidence threshold is found:

```
tags: title + artist  →  any result?  →  show candidates
          ↓ no
tags: title alone     →  any result?  →  show candidates
          ↓ no
cleaned filename      →  any result?  →  show candidates
          ↓ no
→ mark as no_mb_match, move on
```

### Search source comparison

| Service | Auth required | Strengths for this use case |
|---|---|---|
| **iTunes Search API** (Apple) | None | Apple Music catalog; excellent coverage of Tamil and Hindi film music; clean structured data; no rate limit documented |
| **Deezer API** | None | Good mainstream coverage; decent Indian music catalog; straightforward JSON response |

iTunes is queried with no API key or account and has no published rate limit. Deezer is
available as a future extension.

The pass labels each candidate with which signal was used (tags vs filename) so the user
can judge the result in context.

---

---

## ACRCloud pass for pre-2000 Indian film music (2026-04-10, issue #33)

### Why ACRCloud covers what Shazam misses

ACRCloud has formal licensing agreements with **Saregama (formerly HMV India)**,
which holds the largest archive of pre-2000 Tamil and Hindi film music. These
tracks were catalogued and ingested into ACRCloud's Recorded Music database as
part of Saregama's digital licensing programme. They are absent from Shazam's
database, which skews toward post-2000 digital releases.

Practical implication: songs from 1960s–1990s Tamil and Hindi films that return
`no_match` from Shazam have a meaningful probability of being in ACRCloud's
Saregama-sourced catalog.

### Implementation

Single probe per song (to conserve the 1,000/day free-tier quota):
- Start position: `max(10s, duration × 35%)` — skips most intros
- Fingerprint window: 12 seconds
- No interactive review — fully automated, same as `--multiprobe`
- `id_source='acrcloud'` on match
- Cover art not available in ACRCloud free-tier responses

### Rate limit and quota strategy

ACRCloud free tier: **1,000 queries/day**, resetting at **midnight UTC (7pm US Eastern)**.

With two runs per US calendar day:
| Run | When (EST) | Songs processed |
|---|---|---|
| Run A | Morning/afternoon | up to 900 |
| Run B | After 7pm EST (midnight UTC resets quota) | up to 900 |
| **Total** | **Per US day** | **~1,800** |

At 1,800/day, the full 5,500+ no_match pile can be covered in ~3 days.
Use `--limit N` to control how many songs to process per run (default 900).

### Comparison with Shazam multiprobe

| | `--multiprobe` | `--acrcloud` |
|---|---|---|
| Database | Shazam (~200M tracks) | ACRCloud Recorded Music (Saregama catalog) |
| What it recovers | Correct songs probed at the wrong window | Songs absent from Shazam's DB entirely |
| Cost | Free, unlimited | Free, 1,000/day |
| Speed | ~2s/song | ~1s/song |
| Automation | Full | Full |

Run `--multiprobe` first (no quota limit), then `--acrcloud` on the remaining pile.

---

## Multi-probe Shazam strategy (2026-04-09, issue #32)

### Why the default probe misses

ShazamIO's `recognize()` sends a single ~10-second fingerprint window per file.
For songs longer than 36 seconds, it automatically skips to the midpoint
(`converter.py:125`). For shorter songs it starts from the beginning.

Older Tamil and Hindi film music frequently opens with a 30–60 second
orchestral intro before the main vocals begin. Shazam's fingerprint database
indexes the chorus and vocal hook — not the intro. The default midpoint probe
often lands in the intro for these songs, missing the indexed section entirely.

**Evidence:** Phone Shazam tests on songs that the pipeline returned `no_match`
confirmed they are in Shazam's database. The phone app worked because the user
held it during the chorus, not the intro.

### The fix — four probes per file

A new automated pass (`--multiprobe`, `pipeline/multiprobe_pass.py`) probes
each `no_match` file at four positions: **15%, 35%, 55%, and 75%** of the
song's duration. For each probe it extracts a 15-second WAV slice (pydub),
passes the bytes to `shazam.recognize(bytes)` — supported natively by the
ShazamIO Rust core — and stops at the first match.

| Parameter | Value |
|---|---|
| Probe positions | 15%, 35%, 55%, 75% of duration |
| Window per probe | 15 seconds |
| Max API calls per song | 4 |
| Sleep between probes | `SHAZAM_SLEEP_SEC` (2s) — same as main pass |
| id_source on match | `shazam-multiprobe` |

### What this does not solve

Songs that are genuinely absent from Shazam's database — obscure regional
tracks, private recordings, or very early film music (pre-1970) with no digital
catalogue presence — will not be identified by any number of probes. The
`--multiprobe` pass converts "wrong window" misses into hits; it cannot create
fingerprint data that does not exist.

---

## Late design discussion — ID3 artist name transliteration (2026-04-04)

### Context

This discussion happened after v1.1.0 was released and a 5,550-file batch run was already
in progress. It should have been had before Stage 4 (tagging) was designed.

The collection originates from the early iPod era, when organising Indian music by folder
structure (Tamil/, Hindi/) was the primary way to browse. At that time, having artist names
in native script (Tamil, Devanagari) in the ID3 tags would have been meaningful — it is now
a quality-of-life improvement for any player or library that renders tag metadata.

### The problem with the original design

The original design left artist names in their Romanised form as returned by Shazam (e.g.
`A.R. Rahman`, `Lata Mangeshkar`, `Ilaiyaraaja`). Shazam always returns metadata in
Roman script regardless of the song's language. No transliteration pass was planned.

### What was evaluated

Sarvam AI — an LLM specialising in Indian languages — was tested on 2026-04-04.

**API:** `POST https://api.sarvam.ai/transliterate`
**Docs:** https://docs.sarvam.ai/api-reference-docs/text/transliterate-text
**Auth:** `api-subscription-key` header — requires a free account at sarvam.ai
**Pricing:** Free tier provides INR 1,000 credit. No binary dependency.

Three test calls:

| Input (Roman) | Target | Output (native script) |
|---|---|---|
| `A.R. Rahman` | Tamil (ta-IN) | `ஏ.ஆர். ரஹ்மான்` |
| `Lata Mangeshkar` | Hindi (hi-IN) | `लता मंगेशकर` |
| `Ilaiyaraaja` | Tamil (ta-IN) | `இளையராஜா` |

All three results were accurate.

### Decision — if implemented

**The target script must follow the song's language, not the artist's origin language.**

Rationale: the same artist (e.g. A.R. Rahman) composes for both Tamil and Hindi films.
Writing his name in Tamil script on a Tamil song and in Devanagari on a Hindi song is
correct — the script should match the linguistic context of the track, not a canonical
"home language" for the artist.

Concretely:
- Song `language = 'Tamil'` → artist name transliterated to `ta-IN`
- Song `language = 'Hindi'` → artist name transliterated to `hi-IN`
- Song `language = 'English'` → no transliteration, keep Roman

Compound artist strings (e.g. `"A.R. Rahman & Lata Mangeshkar"`) must be split on `&`
and `,`, each component transliterated independently, then reassembled.

Only the `final_artist` ID3 field is in scope — filenames and folder names are unchanged.

### Caching — `artist_transliterations` table

To minimise API calls (and protect the free-tier credit), all transliteration results are
stored in a dedicated DB table keyed on `(roman_name, language)`. Subsequent runs do a
table lookup first and only call Sarvam for names not already cached. A name that appears
in 200 songs (e.g. Ilaiyaraaja) costs exactly one API call.

### What was not resolved

The `language` field in the DB is derived from the input folder structure, which has known
inaccuracies (English-language artists filed under Tamil/Hindi folders and vice versa).
A reliable language classifier for the song itself — independent of folder structure —
would be needed before a bulk transliteration run to avoid mis-scripting artist names.
Accepted as ~5–10% tolerable noise for v1.2.0. Tracked as a future improvement in
GitHub issue #25.

---

---

## Late design discussion — GUI query tool scope (2026-04-04)

### What it is

A read-only natural language query interface over `music.db`. The user types plain English
("show me all Tamil songs from 1981", "find everything flagged for review") and a Claude
API call converts it to SQL, runs it, and returns results as a table.

That is the full scope. It does not write to the DB. It does not write to the filesystem.
It does not re-tag files. It does not move files.

### NL → SQL implementation — why Claude API + direct SQLite

Several options were evaluated before choosing the implementation approach:

| Option | Verdict | Reason |
|---|---|---|
| **Claude API + direct SQLite** ✅ | Chosen | 50 lines of Python, no training, excellent SQL quality for a 15-column schema, handles ambiguous language well |
| LlamaIndex NLSQLTableQueryEngine | Overkill | Adds abstraction overhead; API breaks between minor versions; no advantage for a single table |
| LangChain SQLDatabaseChain | Avoid | Actively deprecated and reshuffled into `langchain-community`; fragmented docs |
| Vanna.ai | Over-engineered | Requires a vector store + 20–30 training Q&A pairs; justified for complex schemas, not this one |
| SQLCoder (Defog, local model) | Niche | Needs GPU for usable speed; best open-source SQL model but overkill for simple queries |
| Ollama + raw prompting | Valid fallback | 80–90% of Claude quality for simple queries; use if offline operation is needed |

**Key implementation details:**
- Claude model: `claude-sonnet-4-6`, temperature **0.2** (deterministic SQL, not creative output)
- Schema + status values + language values embedded in the system prompt
- Hard `SELECT`-only guard: any non-`SELECT` query is rejected before execution
- 5–10 example Q&A pairs in the system prompt improve consistency for domain terms
- **Requires a Claude API key** — set via `ANTHROPIC_API_KEY` environment variable

### What it is not — and why

An earlier draft of this feature included inline editing, field correction, re-tagging,
and file moves triggered from the GUI. That scope was explicitly rejected.

**Rationale:**

The intended user of this tool is not computer-illiterate. This is a power-user pipeline
for someone who is comfortable with a terminal. A person who cannot operate a command line
has no MP3 collection with this level of disorganisation in the first place — they signed
up for iTunes or Spotify and never had the problem.

Building write-back into the GUI would add significant complexity (DB write + Mutagen
re-tag + filesystem move must all succeed atomically) for no real benefit: the same user
can navigate to the right folder and run a CLI command in seconds.

### How data quality issues are surfaced

The GUI displays flagged records (`error_msg LIKE 'REVIEW:%'`) as a dedicated queue.
For each flagged song it shows the `final_path` and a help line with the exact CLI
command the user needs to run to correct it — e.g.:

```
File:    Music/English/1900/Country Tunes, Vol. 4/A Fool Such as I.mp3
Issue:   REVIEW: bogus year 1900 — Jim Reeves was active 1950s–60s
Fix via: python main.py --review --folder "Music/English/1900"
```

The user reads the hint, opens a terminal, runs the command. The GUI is an inspector
and navigator, not an editor.

### Transliteration

Transliteration of ID3 artist tags (Sarvam AI) runs as a batch pipeline pass, not from
the GUI. De-duplicating by unique artist name before calling the API (e.g. Ilaiyaraaja
appears 200 times but is only one API call) is handled in the batch pass. The GUI has
no role in transliteration.

### UX philosophy — what to tell users

The GUI should be upfront about who it is and is not for. Somewhere visible — the landing
page or a prominent About section — it should say something like:

> **Not for everyone — and that's intentional.**
>
> If you want your music organised without any of this, just use iTunes. It does the job
> beautifully for most people and you will never need this tool.
>
> This pipeline exists for a specific problem: large collections of Tamil and Hindi MP3s
> from the pre-streaming era, ripped from CDs, with garbled filenames, wrong tags, and
> no consistent structure. If that is not your problem, stop here.
>
> If it is your problem, the query tool below works like a report menu. A set of standard
> reports is always available. If none of them fit, just describe what you want in plain
> English — "show me all Tamil songs where the album is unknown" — and it will generate
> the report on the fly. You do not need to know SQL. You do not need Crystal Reports or
> Power BI. In the AI age, you describe the report you need and it gets built for you,
> for your exact use case, instantly. That is the only shift required from the old way of
> working with canned reports.

This sets expectations correctly, keeps the tool from being misused, and explains the
NL → SQL capability in terms that anyone who has used Crystal Reports or similar tools
will immediately understand.

---

## Links

[README.md](../README.md) | [Architecture](ARCHITECTURE.md) | [Database Reference](DATABASE.md)
