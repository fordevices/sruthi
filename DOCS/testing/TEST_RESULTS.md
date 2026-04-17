# System Test Results

**Session date:** 2026-04-02 / 2026-04-03
**Tester:** max-kirahi
**Pipeline version:** post-issues #1–#7, pre-release
**Test document:** [SYSTEM_TESTING.md](SYSTEM_TESTING.md)

---

## Summary

| Result | Count |
|---|---|
| PASS | 14 |
| FAIL | 2 |
| DEFERRED | 3 |
| Total | 19 |

**Bugs filed during testing:** 9 (issues #14–#24, excluding #15 which is a feature)
**Release blocking bugs:** 3 (#20, #23, #24)

---

## Test case results

| TC | Description | Result | Notes |
|---|---|---|---|
| TC-01 | Happy path — Shazam full pipeline | ✓ PASS | Clean run, correct path, tags verified on disk |
| TC-02 | Collection-fix path | DEFERRED | File used was identified by Shazam directly; needs a file Shazam cannot identify with `(From <Album>)` in filename |
| TC-03 | Short file → no_match | ✓ PASS | 2.9s file correctly caught, `⚠ too short` output, no Shazam call |
| TC-04 | No match — Shazam fails | ✓ PASS | `no_match` status set correctly, correct terminal output |
| TC-05 | Manual review — enter metadata | ✓ PASS | Play, edit, confirm all worked; partial entry (title only) saved correctly |
| TC-06 | Partial override — fix year only | ✓ PASS | `\| \| \| 2026` syntax worked; other fields kept as-is |
| TC-07 | Skip and come back | ✓ PASS | Demonstrated naturally during TC-05; file reappeared on next `--review` |
| TC-08 | Metadata search pass | ✓ PASS | Search, play, pick, accept all worked; `--move` completed correctly after |
| TC-09 | AcoustID pass | ✓ PASS | No match found (expected for Tamil collection); no crash, clean output |
| TC-10 | Duplicate detection | ✓ PASS | Files correctly routed to `Duplicates/`; terminal display shows wrong path (bug #22) |
| TC-11 | Error recovery | ✗ FAIL | Error files permanently skipped by Stage 1 hash dedup — never retried (bug #23) |
| TC-12 | Dry run — no state changes | ✗ FAIL | Stage 1 still wrote new records to DB during `--dry-run` (bug #24) |
| TC-13 | Resume safety — interrupt and re-run | ✓ PASS | Ctrl-C mid-run left DB intact; re-run skipped already-processed files correctly |
| TC-14 | Renamed no_match file re-picked | ✓ PASS | `[PATH] path updated for max-000023` — hash matched, DB path updated correctly |
| TC-15 | `--review --flagged` | DEFERRED | Needs large batch to get a Shazam bad-year result naturally |
| TC-16 | `--stats` output | ✓ PASS | Confirmed repeatedly throughout session; counts accurate across all runs |
| TC-17 | `--zeroise` confirmation guard | ✓ PASS | `y` and `es` both aborted; DB unchanged; requires exact `YES` |
| TC-18 | `--move` without source path | ✓ PASS | Run many times throughout session without issues |
| TC-19 | `--move --dry-run` | ✓ PASS | Stats unchanged before and after; 5 songs previewed, nothing written |
| TC-20 | `--review --folder` | PENDING | Issue #15 not yet implemented |

---

## Bugs found during testing

| Issue | Severity | TC found | Description | Status |
|---|---|---|---|---|
| #14 | Low | Pre-test | Stale feature branches after merged PRs (#8, #9, #10) | Open — deleted by user during session |
| #16 | Medium | TC-05 | `increment_duplicate_count` fires on re-runs of non-done files | Open |
| #17 | Low | TC-05 | `--stats` hint says `python` instead of `python3` | Open |
| #19 | Low | TC-08 | `--metadata-search` output header still says "Filename pass" | Open |
| #20 | **High** | TC-08 | `--metadata-search` missing `return` — argparse usage prints after completion | Open |
| #21 | Low | TC-10 | `find_done_duplicate` query — COALESCE fix applied; original diagnosis corrected | Open (minor) |
| #22 | Medium | TC-10 | Terminal shows wrong path and `✓ moved` instead of `⓪ duplicate` for Duplicates/ | Open |
| #23 | **High** | TC-11 | Error files permanently stuck — hash dedup skips `error` status same as `done` | Open |
| #24 | **High** | TC-12 | `--dry-run` does not prevent Stage 1 from writing new records to DB | Open |

### Features filed during testing

| Issue | TC | Description |
|---|---|---|
| #15 | TC-02 | `--review --folder=PATH` filter to scope review queue to a folder |
| #18 | TC-08/09 | Document recommended no_match workflow order (Shazam → AcoustID → metadata search → review) |

---

## Notable observations

**AcoustID yield for Indian film music:** Across ~280 Tamil/Hindi files tested over multiple sessions, AcoustID has found zero matches for files that Shazam also failed on. MusicBrainz/AcoustID's community database has significantly less coverage of Indian film music compared to Shazam. The pass is still worth running as it costs nothing, but user expectations should be set accordingly. Tracked in issue #18.

**Duplicate detection display:** The duplicate logic routes files to `Duplicates/` correctly (confirmed in DB and on disk), but the terminal always shows `✓ moved → <standard path>` due to the stale song dict read bug (#22). Users seeing the terminal output would incorrectly believe duplicates are overwriting originals.

**Metadata search pass rename:** The `--filename-match` flag was renamed to `--metadata-search` during this session. Two cosmetic artefacts remain: the output header (#19) and the missing `return` (#20).

**TC-14 note:** The renamed file path-update fix only triggers when the renamed file is still within the scanned `Input/` folder. Moving a file outside the scan path leaves the DB entry stale and will cause a Stage 3 error on the next `--move`. This is expected behaviour but should be documented as a user warning.

---

## Release readiness

### Blocking bugs (must fix before v1.1.0)

| Issue | Why blocking |
|---|---|
| #20 | `--metadata-search` prints argparse usage after every run — looks broken |
| #23 | Error files permanently stuck with no recovery path — silent data loss risk |
| #24 | `--dry-run` modifies DB — fundamentally breaks the preview contract |

### Non-blocking bugs (fix in v1.1.x)

| Issue | Why non-blocking |
|---|---|
| #16 | Spurious `duplicate_count` increment — cosmetic warning in `--review`, no data loss |
| #17 | Wrong Python hint in `--stats` — cosmetic |
| #19 | Wrong header in metadata search output — cosmetic |
| #22 | Wrong terminal path for duplicates — display only, logic correct |

### Deferred tests

| TC | Condition to test |
|---|---|
| TC-02 | Need an MP3 that Shazam cannot identify but whose filename contains `(From <Album>)` |
| TC-15 | Need a large batch run where Shazam returns a year outside 1940–present |
| TC-20 | Waiting on implementation of issue #15 |

---

## Links

[System Testing Guide](SYSTEM_TESTING.md) | [Architecture](ARCHITECTURE.md) | [User Guide](USER_GUIDE.md)
