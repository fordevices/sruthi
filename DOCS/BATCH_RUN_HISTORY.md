# Batch Run History

Record of every full batch run against the Input/ library.
Update this after each run with the summary.json stats and any observations.

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
