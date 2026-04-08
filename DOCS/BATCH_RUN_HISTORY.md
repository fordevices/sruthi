# Batch Run History

Record of every full batch run against the Input/ library.
Update this after each run with the summary.json stats and any observations.

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
