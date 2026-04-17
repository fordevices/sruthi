# Batch Run History

Record of every full batch run against the Input/ library.
Update this after each run with the summary.json stats and any observations.

---

## Run 10 — 2026-04-17 (ACRCloud Hindi — new batch day 1)

| Field | Value |
|---|---|
| Date | 2026-04-17 |
| Passes run | `--acrcloud --language Hindi --limit 900`, `--move` |
| Stages | 3 (tag), 4 (move) |
| DB zeroed before run | No |

### ACRCloud Pass — Hindi (new batch, day 1)

| Metric | Count |
|---|---|
| Songs submitted | ~1,310 |
| Identified | 1,066 |
| No match | ~244 |
| Errors | 1 (corrupt MP3, Header size not synchsafe) |
| Hit rate | **~81%** |
| id_source | `acrcloud` |
| API calls used | ~1,000 (of 1,000/day free quota) |
| Hindi songs deferred | 195 |

### Move — ACRCloud Hindi results

| Metric | Count |
|---|---|
| Tagged | 1,066 |
| Moved | 1,066 |
| Errors | 0 |

### End-of-session DB state

| Status | Count |
|---|---|
| done | 11,580 |
| no_match | 2,235 |
| error | 19 |

### Backlog breakdown

| Bucket | Count |
|---|---|
| Not yet tried with ACRCloud | 195 |
| Tried ACRCloud, still no_match | 2,040 |
| **Total unidentified** | **2,235** |

### Observations

- Best ACRCloud hit rate yet at ~81% — 1985–1999 Bollywood is well-covered in the Saregama catalog.
- 195 songs still untried; one more ACRCloud run tomorrow will exhaust the new batch.
- Bug fixed mid-run: corrupt MP3 (`Header size not synchsafe`) crashed `acrcloud_pass.py` at song 311 — same fix applied as issue #36, also patched `multiprobe_pass.py` proactively.
- Quota reset needed before continuing (midnight UTC / 7pm EST).

---

## Run 9 — 2026-04-17 (Shazam — new Hindi batch: best-of-90s 1985–1999)

| Field | Value |
|---|---|
| Date | 2026-04-17 |
| Passes run | `python3 main.py Input/Hindi/best-of-90s-1985-1999-bollywood-songs/`, `--move` |
| Stages | 1 (identify), 3 (tag), 4 (move) |
| DB zeroed before run | No |

### Source batch

| Detail | Value |
|---|---|
| Collection | Best of 90s [1985–1999] — Bollywood Songs |
| Files extracted | 2,685 MP3s (after removing 29 non-MP3 files: WMA, XML, torrent, PDF, sqlite) |
| Bit rate | 320 Kbps |
| Filename format | `Song Title - Singer(s) - Movie.mp3` |

### Stage 1 — Shazam identification

| Metric | Count |
|---|---|
| Files total | 2,685 |
| Identified | ~1,209 (first run) + 103 (second run after crash) = ~1,312 |
| No match | ~1,493 |
| Errors | 11 (corrupt MP3s — Header size not synchsafe) |
| Hit rate | **~48%** |

### Move

| Metric | Count |
|---|---|
| Tagged | 1,179 |
| Moved | 1,280 |
| Errors | 0 |

### Bugs fixed this session

| Issue | Module | Description |
|---|---|---|
| #36 | `identify.py` | Corrupt MP3 (`Header size not synchsafe`) crashed Stage 1 — `ID3Error` not caught |
| #37 | `USER_GUIDE.md` | Added warning: never run two pipeline passes simultaneously (SQLite locking) |
| #38 | `tagger.py` | `get_connection` used but not imported — crash on any tagging error |

### Observations

- Shazam hit rate of ~48% — lower than expected for 1985–1999 mainstream Bollywood.
- Pipeline crashed twice: once in Stage 1 (corrupt MP3, issue #36) and once in Stage 3 (missing import, issue #38). Both fixed and re-run successfully.
- Async Stage 1 processing means some in-flight songs weren't committed on crash — re-run correctly re-processed those, all identified (100% rate on the small catch-up batch).
- Clean filename format (`Song Title - Singer(s) - Movie`) means `--metadata-search` should perform very well on remaining no_match songs from this batch.
- Issue #39 raised: duplicate detection picks first-moved version regardless of year — can cause 2020 re-releases to win over 1994 originals.

---

## Run 8 — 2026-04-15 (ACRCloud Hindi day 4 — final)

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Passes run | `--acrcloud --language Hindi --limit 900`, `--move` |
| Stages | 3 (tag), 4 (move) |
| DB zeroed before run | No |

### ACRCloud Pass — Hindi (day 4, final)

| Metric | Count |
|---|---|
| Songs submitted | 614 |
| Identified | 392 |
| No match | 222 |
| Errors | 0 |
| Hit rate | **63.8%** |
| id_source | `acrcloud` |
| API calls used | 614 (of 1,000/day free quota) |
| Hindi ACRCloud backlog | **exhausted** |

### Move — ACRCloud Hindi results

| Metric | Count |
|---|---|
| Tagged | 392 |
| Moved | 392 |
| Errors | 0 |

### End-of-session DB state

| Status | Count |
|---|---|
| done | 9,234 |
| no_match | 1,808 |
| error | 7 |

### Backlog breakdown

| Bucket | Count |
|---|---|
| Not yet tried with ACRCloud | ~12 |
| Tried ACRCloud, still no_match | ~1,796 |
| **Total unidentified** | **1,808** |

### Observations

- Hit rate rebounded to 63.8% on the final batch — the queue likely contained a richer
  slice of the Saregama catalog (Lata Mangeshkar, Hemant Kumar tracks identified).
- Hindi ACRCloud backlog is now fully exhausted. Only ~12 songs remain untried
  (likely too-short or corrupt files).
- 1,796 no_match songs have been tried by ACRCloud and remain unidentified —
  these are the candidates for `--metadata-search`.
- Hindi ACRCloud totals across all 4 days: ~614+900+900+100 = 2,514 submitted,
  ~392+359+223+40 = 1,014 identified (~40% aggregate hit rate).
- New `--mark-removed` command available (v1.3.0): delete unwanted files from Input/
  then run `python3 main.py --mark-removed` to retire them from the DB before
  running `--metadata-search`.

---

## Run 7 — 2026-04-14 (ACRCloud Hindi day 3)

| Field | Value |
|---|---|
| Date | 2026-04-14 |
| Passes run | `--acrcloud --language Hindi --limit 900`, `--move` |
| Stages | 3 (tag), 4 (move) |
| DB zeroed before run | No |

### ACRCloud Pass — Hindi (day 3)

| Metric | Count |
|---|---|
| Songs submitted | 900 |
| Identified | 359 |
| No match | 541 |
| Errors | 0 |
| Hit rate | **39.9%** |
| id_source | `acrcloud` |
| API calls used | 900 (of 1,000/day free quota) |
| Hindi songs deferred | ~614 |

### Move — ACRCloud Hindi results

| Metric | Count |
|---|---|
| Tagged | 359 |
| Moved | 359 |
| Errors | 0 |

### End-of-session DB state

| Status | Count |
|---|---|
| done | 8,842 |
| no_match | 2,200 |
| error | 7 |

### Backlog breakdown

| Bucket | Count |
|---|---|
| Not yet tried with ACRCloud (Hindi) | ~614 |
| Tried ACRCloud, still no_match | ~1,574 |
| **Total unidentified** | **2,200** |

### Observations

- Hit rate rebounded to 39.9% (vs 24.8% on day 2) — may have been luck of the draw
  in the queue ordering, or the 900-song window happened to hit a richer portion.
- ~614 Hindi songs still untried; one more day at 900/day will exhaust the Hindi backlog.
- After Hindi ACRCloud is done, ~1,574 songs have been tried and remain no_match —
  candidates for `--metadata-search`.

---

## Run 6 — 2026-04-13 (ACRCloud Hindi day 2 + move backlog)

| Field | Value |
|---|---|
| Date | 2026-04-13 |
| Passes run | `--move` (backlog from 2026-04-11), `--acrcloud --language Hindi --limit 900`, `--move` |
| Stages | 3 (tag), 4 (move) |
| DB zeroed before run | No |

### Move — backlog from 2026-04-11 (660 songs)

Songs identified in the 2026-04-11 ACRCloud session (620 Tamil + 40 Hindi) that had not yet been moved.

| Metric | Count |
|---|---|
| Tagged | 660 |
| Moved | 659 |
| Errors | 1 (max-008133 — path resolved to None) |

### ACRCloud Pass — Hindi (day 2)

| Metric | Count |
|---|---|
| Songs submitted | 900 |
| Identified | 223 |
| No match | 677 |
| Errors | 0 |
| Hit rate | **24.8%** |
| id_source | `acrcloud` |
| API calls used | 900 (of 1,000/day free quota) |
| Hindi songs deferred | ~1,514 |

### Move — ACRCloud Hindi results

| Metric | Count |
|---|---|
| Tagged | 223 |
| Moved | 223 |
| Errors | 0 |

### End-of-session DB state

| Status | Count |
|---|---|
| done | 8,483 |
| no_match | 2,559 |
| error | 7 |

### Backlog breakdown

| Bucket | Count |
|---|---|
| Not yet tried with ACRCloud | 1,526 |
| Tried ACRCloud, still no_match | 1,033 |
| **Total unidentified** | **2,559** |

### Observations

- Hindi ACRCloud hit rate dropped to 24.8% (vs 40% on day 1 of 100 songs) — likely the
  harder, older tracks remain in the queue.
- ~1,514 Hindi songs still untried; at 900/day will take ~2 more days to exhaust.
- 1,033 songs have been tried by ACRCloud and remain no_match — candidates for
  `--metadata-search` once the ACRCloud backlog is cleared.
- Quota resets midnight UTC / 7pm EST.

---

## Run 5 — 2026-04-11 (ACRCloud Tamil + Hindi day 1 + docs rewrite)

| Field | Value |
|---|---|
| Date | 2026-04-11 |
| Passes run | `--acrcloud --language Tamil`, `--acrcloud --language Hindi --limit 100` |
| Stages | 1 (ACRCloud identify only — move deferred) |
| DB zeroed before run | No |

### ACRCloud Pass — Tamil

| Metric | Count |
|---|---|
| Songs submitted | 900 |
| Identified | 620 |
| No match | 280 |
| Errors | 0 |
| Hit rate | **69%** |
| Note | Ran 900 instead of 634 due to quota-wastage bug (re-queried already-tried songs) |

### ACRCloud Pass — Hindi (day 1)

| Metric | Count |
|---|---|
| Songs submitted | 100 |
| Identified | 40 |
| No match | 60 |
| Errors | 0 |
| Hit rate | **40%** |

### Observations

- Tamil ACRCloud essentially exhausted; ~11 songs still untried (9 deferred + ~2 too short).
- Hindi had ~2,344 untried songs remaining after this session.
- Quota-wastage bug identified: `--acrcloud` re-queries songs already tried (id_source='acrcloud',
  status='no_match'), burning daily quota. Fix: add filter in `acrcloud_pass.py`.
- Move was intentionally deferred to next session (660 songs pending).

---

## Run 4 — 2026-04-09/10 (ACRCloud + multiprobe session)

| Field | Value |
|---|---|
| Date | 2026-04-09 to 2026-04-10 |
| Passes run | `--acrcloud` (900 songs), `--multiprobe` (partial, killed) |
| Stages | 3 (tag), 4 (move) |
| DB zeroed before run | No |

### ACRCloud Pass

First run of the `--acrcloud` fingerprint pass (issue #33) targeting pre-2000 Indian film music
via ACRCloud's Recorded Music catalog (includes Saregama/HMV India archive).

| Metric | Count |
|---|---|
| Songs submitted | 900 |
| Identified | ~748 |
| Hit rate | ~83% |
| id_source | `acrcloud` |
| API calls used | 900 (of 1,000/day free quota) |

### Multiprobe Pass

Partial run of `--multiprobe` (issue #32) — killed once ACRCloud was confirmed running,
as the same no_match pool was the target and results were being written concurrently.

| Metric | Count |
|---|---|
| Songs identified (committed to DB) | 163 |
| id_source | `shazam-multiprobe` |

### Organizer Bug Fix (issue #34)

641 songs had `file_path` pointing to `Input/` (already moved in a prior run) while
`final_path` in `Music/` was correct. Stage 4's `shutil.move()` failed for these.
Fix: added guard in `organize_file()` — if source missing but target exists, mark done.
DB recovery: 660 songs updated `error` → `done` where `final_path` existed on disk.

### Stage 4 — Move

| Metric | Count |
|---|---|
| Songs moved to Music/ | 208 |
| Errors | 0 |

### End-of-session DB state

| Status | Count |
|---|---|
| done | 6,394 |
| no_match | 4,649 |
| error | 6 (2 corrupt format, 4 network timeout — genuine) |

### Done breakdown by id_source

| Source | Count |
|---|---|
| shazam | 5,475 |
| acrcloud | 750 |
| shazam-multiprobe | 163 |
| metadata-search | 4 |
| collection-fix | 2 |
| **Total** | **6,394** |

### Observations

- ACRCloud hit rate of ~83% on pre-2000 Indian film music confirms the hypothesis:
  Saregama/HMV catalog is well-represented in ACRCloud but absent from Shazam.
- Multiprobe recovered 163 songs Shazam's single-probe had missed (probing 4 positions
  across the track instead of just the midpoint).
- Combined new identified this session: 913 songs (6,394 − 5,481 from Run 3).
- 4,649 songs remain no_match — mostly pre-2000 Tamil and Hindi tracks.
- ACRCloud free trial: 14 days from signup, 1,000 queries/day.
  Next runs: queue another 900-song batch after quota reset (midnight UTC).

---

## Run 3 — 2026-04-08 (overnight)

| Field | Value |
|---|---|
| Run ID | `2026-04-08_22-52-09` |
| Started | 2026-04-08 22:52 |
| Finished | 2026-04-09 01:40 |
| Duration | 2h 49m (10,125s) |
| Source | `Input/Hindi/` |
| Stages | 1, 3, 4 |
| DB zeroed before run | No |

### Stage 1 Results

| Metric | Count | % of total |
|---|---|---|
| Files total | 3,015 | 100% |
| Newly identified | 524 | 17% |
| No match | 2,444 | 81% |
| Already done (skipped) | 45 | 1% |
| Errors | 2 | <1% |
| Shazam calls made | 2,968 | — |

### End-of-run DB state

| Status | Count |
|---|---|
| done | 5,481 |
| no_match | 5,562 |
| error | 6 |

### Language breakdown (full DB)

| Language | Count |
|---|---|
| Tamil | 5,267 |
| Hindi | 3,153 |
| English | 2,629 |

### Observations

- Hindi library match rate was 17% — significantly lower than Hindi in Run 1 (78%).
  Likely older/obscure tracks with low Shazam coverage, similar to Tamil pre-2000 music.
- no_match pile grew from 3,118 → 5,562 (+2,444); done grew 4,957 → 5,481 (+524).
- 2 new errors; 45 files already done (skipped correctly).
- `--move` run on 2026-04-09 filed all 524 newly identified songs.

---

## Run 2 — 2026-04-08

| Field | Value |
|---|---|
| Run ID | `2026-04-08_08-14-07` |
| Started | 2026-04-08 08:14 |
| Finished | 2026-04-08 11:49 |
| Duration | 3h 35m (12,902s) |
| Source | `Input/Tamil` (Tamil re-run + error retry) |
| Stages | 1, 3, 4 |
| DB zeroed before run | No |

### Stage 1 Results

| Metric | Count | % of total |
|---|---|---|
| Files total | 3,879 | 100% |
| Newly identified | 1,101 | 28% |
| No match | 1,506 | 39% |
| Already done (skipped) | 1,271 | 33% |
| Errors (network timeouts) | 591 | 15% |
| Shazam calls made | 2,607 | — |

### Error retry (same day)

594 songs in `error` status were retried after fixing a bug where the 1-second
Shazam rate-limit sleep was applied to skipped files, making re-runs ~70 minutes
slower than necessary (#29). On retry with the fix in place:

| Metric | Count |
|---|---|
| Retried | 594 |
| Identified on retry | 576 |
| No match on retry | 15 |
| Still errored | 2 |
| **Retry success rate** | **97%** |

All 121 tagging failures (Errno 13 — permission denied, files owned by different
user) were resolved with `sudo chown` and successfully tagged and moved.

### End-of-day state

| Status | Count |
|---|---|
| done | 4,859 |
| no_match | 3,218 |
| error | 2 (corrupt files — "Unrecognized format") |

### Observations

- **97% of errors were network timeouts**, not genuine identification failures.
  All retried successfully once the sleep-on-skip bug was fixed.
- Tamil is the dominant no-match language — 3,218 remaining no_match files are
  almost entirely Tamil, consistent with Run 1 observations on pre-2000 coverage.
- MusicBrainz removed from `--metadata-search` this session (#28) — iTunes only.
- Next steps: `--metadata-search` on the 3,218 no_match files; then manual
  `--review` for anything iTunes can't resolve.

---

## Run 1 — 2026-04-04

| Field | Value |
|---|---|
| Run ID | `2026-04-04_17-34-04` |
| Started | 2026-04-04 17:34 |
| Finished | 2026-04-04 23:33 |
| Duration | 5h 59m (21,550s) |
| Source | `Input/` (full library) |
| Stages | 1, 2 (skipped), 3, 4 |
| DB zeroed before run | Yes |

### Results

| Metric | Count | % of total |
|---|---|---|
| Files total | 5,550 | 100% |
| Identified + moved | 3,768 | 68% |
| No match | 1,700 | 31% |
| Already done (skipped) | 78 | 1% |
| Errors | 4 | <1% |
| Shazam calls made | 5,468 | — |

### No-match breakdown by language

| Language | No match | Total in library | Hit rate |
|---|---|---|---|
| Tamil | 1,159 | ~2,659 | ~56% |
| English | 501 | ~2,626 | ~81% |
| Hindi | 40 | ~183 | ~78% |

### Observations

- Tamil no-match rate (44%) is the biggest gap — likely older pre-2000 film music
  with low Shazam coverage. Same gap seen historically with AcoustID + MusicBrainz.
- Hindi and English hit rates are solid (78–81%).
- Stages 3 and 4 were clean — 3,768 moved, 0 errors.
- The 4 identification errors are in the `error` status in the DB.
- Stage 2 (manual review) was skipped — `--review-after` flag not used.
- Next steps: `--metadata-search` pass on the 1,700 no_match files;
  transliteration of ID3 artist tags (design decision recorded in DESIGN_DECISIONS.md).

---
