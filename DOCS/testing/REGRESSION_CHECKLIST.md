# Regression Checklist

Run this before any release tag. It covers the critical paths and every bug that has been
fixed at least once — the areas most likely to regress.

---

## Setup — place test fixtures before running

Test files are stored in `tests/fixtures/Tamil/` in the repo. Copy them into `Input/Tamil/`
before starting:

```bash
cp tests/fixtures/Tamil/*.mp3 Input/Tamil/
```

### Fixture manifest

| File | Expected Stage 1 outcome |
|---|---|
| `Anthaathi.mp3` | ✓ identified — Shazam matches |
| `Malare_Oru_Varthai.mp3` | ✓ identified — Shazam matches |
| `Mana_Madurai.mp3` | ✓ identified — Shazam matches |
| `Mei_Nigara.mp3` | ✓ identified — Shazam matches |
| `Minnal_Oru_Kodi.mp3` | ✓ identified — Shazam matches |
| `Kathi_vaitha.mp3` | ✗ no_match — Shazam returns nothing |
| `Kelakalee_aathu.mp3` | ✗ no_match — Shazam returns nothing |
| `Marandhadhae222.mp3` | ✗ no_match — Shazam returns nothing |

After a successful full-pipeline run, the 5 identified files will be moved out of `Input/Tamil/`
into `Music/Tamil/`. The 3 no_match files stay in `Input/Tamil/`.

---

## Start with a clean DB

```bash
python3 main.py --zeroise   # type YES
python3 main.py --stats     # all counts = 0
```

---

## R-01 — Happy path (Stage 1 → 4)

```bash
python3 main.py Input/
```

Expected:
- `[max-XXXXXX] ✓ identified` then `✓ tagged` then `✓ organised → Music/...`
- `--stats` shows `done: 1`
- File exists on disk at the printed path

---

## R-02 — Resume safety (regression: hash dedup)

Run the same command again on the same folder:

```bash
python3 main.py Input/
```

Expected:
- `[--------] ↷ skipped` for every file already processed
- `--stats` counts unchanged

---

## R-03 — Error file retry (fix: bug #23)

```bash
# Set any done/no_match song to error
python3 -c "from pipeline.db import update_song; update_song('max-000001', status='error', error_msg='manual regression test')"
python3 main.py --stats   # confirm error: 1

# Re-run Stage 1
python3 main.py Input/ --stage 1
```

Expected:
- The error file is processed again (not skipped)
- `--stats` shows `error: 0` after the run
- Song progresses to `identified` or `no_match` (not stuck at `error`)

---

## R-04 — Dry run does not write to DB (fix: bug #24)

Add one or two new MP3s to `Input/` that are not yet in the DB. Then:

```bash
python3 main.py --stats                    # note current counts
python3 main.py Input/ --dry-run
python3 main.py --stats                    # must match counts from before
```

Expected:
- Stage 1 log line: `[DRY RUN] Stage 1 skipped`
- Stages 3+4 log lines: `[DRY RUN] would tag / would move`
- DB counts identical before and after
- No files moved on disk

---

## R-05 — `--metadata-search` exits cleanly (fix: bug #20)

Ensure at least one `no_match` song is in the DB (run TC-04 if needed), then:

```bash
python3 main.py --metadata-search
```

Expected:
- Interactive candidate review runs normally
- After quitting (`q`), the shell prompt returns — **no argparse usage error printed**

---

## R-06 — `--move --dry-run` (stages 3+4 dry run)

Ensure at least one `identified` song is in the DB, then:

```bash
python3 main.py --stats                    # note identified count
python3 main.py --move --dry-run
python3 main.py --stats                    # identified count must be unchanged
```

Expected:
- Output shows `[DRY RUN] would tag` and `[DRY RUN] would move` lines
- DB status unchanged; no files moved

---

## R-07 — Renamed no_match file re-picked (regression: path update)

```bash
# Rename a no_match file within Input/
mv "Input/Tamil/old_name.mp3" "Input/Tamil/new_name.mp3"
python3 main.py Input/Tamil/ --stage 1
```

Expected:
- `[PATH]  path updated for max-XXXXXX: .../new_name.mp3`
- DB `file_path` now points to the renamed file
- `--metadata-search` or `--review` can find and process the file

---

## Pass criteria

All 7 checks must pass. Any failure → file a bug before tagging the release.

---

## How to re-run this checklist in a future session

Start a new Claude Code session in this repo and send:

> "Run the regression checklist in DOCS/REGRESSION_CHECKLIST.md and report each result.
> Capture the results in a new DOCS/REGRESSION_RESULTS_<date>.md file and push it."

Claude will execute each check, report PASS/FAIL per item, file any bugs found, and push
the results document. Do this before every release tag.

---

## Links

[System Testing Guide](SYSTEM_TESTING.md) | [Test Results](TEST_RESULTS.md) | [Architecture](ARCHITECTURE.md)
