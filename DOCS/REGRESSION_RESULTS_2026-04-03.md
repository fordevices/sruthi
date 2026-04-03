# Regression Test Results — 2026-04-03

**Tester:** max-kirahi (run by Claude Code)
**Pipeline version:** v1.1.0-rc (post blocking-bug fixes #20, #23, #24)
**Checklist:** [REGRESSION_CHECKLIST.md](REGRESSION_CHECKLIST.md)
**DB state at start:** zeroed clean before run

---

## Summary

| Result | Count |
|---|---|
| PASS | 7 |
| FAIL | 0 |
| Total | 7 |

**Release verdict: CLEAR — no regressions found. Safe to tag v1.1.0.**

---

## Results

| Check | Description | Result | Notes |
|---|---|---|---|
| R-01 | Happy path (Stage 1 → 4) | ✓ PASS | 5 files identified, tagged, moved; disk paths verified |
| R-02 | Resume safety — re-run skips all | ✓ PASS | All 3 remaining files in `Input/Tamil/` skipped cleanly |
| R-03 | Error file retry (bug #23) | ✓ PASS | max-000002 reset from `error` → retried → `no_match`; `error: 0` after run |
| R-04 | Dry run does not write to DB (bug #24) | ✓ PASS | Stage 1 skipped with `[DRY RUN]` message; DB counts identical before and after |
| R-05 | `--metadata-search` exits cleanly (bug #20) | ✓ PASS | Quit with `q`; shell prompt returned cleanly with no argparse usage error |
| R-06 | `--move --dry-run` (stages 3+4 dry run) | ✓ PASS | 5 songs previewed; `identified: 5` unchanged before and after |
| R-07 | Renamed no_match file re-picked | ✓ PASS | `[PATH] path updated for max-000002: .../Kathi_vaitha_renamed.mp3` |

---

## Run details

**Test files used:** 8 MP3s from `tests/fixtures/Tamil/` copied to `Input/Tamil/`
- 5 identified by Shazam: Anthaathi, Malare Oru Varthai, Mana Madurai, Mei Nigara, Minnal Oru Kodi
- 3 no_match: Kathi_vaitha, Kelakalee_aathu, Marandhadhae222

**Execution order note:** R-04 was run first (immediately after zeroise, before any files were in the DB),
then Stage 1 only to populate `identified` rows for R-06, then `--move` to complete R-01,
then R-02, R-03, R-05, R-07 in order. This matches the intent of all checks.

**R-05 observation:** The `--metadata-search` header still reads "Filename pass" — this is the
cosmetic bug #19 (non-blocking, not a regression target for this checklist).

---

## Links

[Regression Checklist](REGRESSION_CHECKLIST.md) | [System Test Results](TEST_RESULTS.md) | [Architecture](ARCHITECTURE.md)
