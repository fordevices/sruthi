# Sruthi — Run Statistics

Results from the full 5,550-file library run, April 4 2026.

---

## Run 1 — April 4 2026

| Field | Value |
|---|---|
| Run ID | `2026-04-04_17-34-04` |
| Started | 2026-04-04 17:34 |
| Finished | 2026-04-04 23:33 |
| Duration | 5h 59m |
| Source | `Input/` (full library — Tamil, Hindi, English) |
| DB zeroed before run | Yes |

### Overall results

| Metric | Count | % of total |
|---|---|---|
| Files total | 5,550 | 100% |
| Identified + moved | 3,768 | 68% |
| No match | 1,700 | 31% |
| Already done (skipped) | 78 | 1% |
| Errors | 4 | <1% |
| Shazam calls made | 5,468 | — |

### Match rate by language

| Language | Matched | No match | Total | Hit rate |
|---|---|---|---|---|
| Tamil | ~1,500 | 1,159 | ~2,659 | ~56% |
| English | ~2,125 | 501 | ~2,626 | ~81% |
| Hindi | ~143 | 40 | ~183 | ~78% |

### Notes

- Tamil no-match rate (44%) is the largest gap — older pre-2000 film music has low Shazam coverage. Same gap seen historically with AcoustID + MusicBrainz.
- Hindi and English hit rates are solid (78–81%).
- Stages 3 and 4 were clean — 3,768 files moved, 0 errors.
- The 4 identification errors remain in the DB with `status=error`.
- Manual review (`--review`) and metadata search (`--metadata-search`) passes are the next step for the 1,700 no-match files.

---

Full run log: `runs/2026-04-04_17-34-04/`
Full run history: [BATCH_RUN_HISTORY.md](BATCH_RUN_HISTORY.md)
