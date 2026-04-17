# System Testing Guide

This document provides a complete end-to-end test plan for Sruthi. Each
test case maps to a specific status transition or feature area. Run through the full suite
after any significant change or before a release.

---

## Prerequisites

Before running any tests:

```bash
# Verify install
python3 main.py --check

# Clear the database to start fresh
python3 main.py --zeroise   # type YES when prompted

# Confirm DB is empty
python3 main.py --stats
# Expected: all counts = 0
```

Have at least the following test files available in `Input/`:

| File | Language | Expected outcome | Notes |
|---|---|---|---|
| A well-known mainstream song | Tamil or Hindi | Shazam identifies it | Use a song released after 1990 |
| A file named like `01_vaseegara_minnale.mp3` | Tamil | Shazam identifies it | Tests track-number-prefixed filename |
| A file with a `(From <Album>)` pattern in the name | Tamil | Collection-fix identified | E.g. `Vaseegara (From Minnale).mp3` |
| A file under 8 seconds | Any | `no_match` (too short) | Trim any MP3 to < 8s with any audio tool |
| A very obscure recording Shazam won't know | Any | `no_match` | Locally recorded audio, noise, or rare track |
| A duplicate of a song already run | Any | Routed to `Duplicates/` | Identical audio content to a song already `done` |

---

## Test cases

### TC-01 — Happy path: Shazam identifies and pipeline completes

**Tests transition:** `pending → identified (shazam) → tagged → done`

1. Place a well-known song in `Input/Tamil/`.
2. Run: `python3 main.py Input/Tamil/`
3. **Expected terminal output:**
   ```
   [max-XXXXXX] ✓ identified  (1/1) Tamil | <Title> — <Artist>
   [max-XXXXXX] ✓ tagged
   [max-XXXXXX] ✓ organised → Music/Tamil/<Year>/<Album>/<Title>.mp3
   ```
4. **Verify in DB:**
   ```bash
   python3 main.py --stats
   # done: 1
   ```
5. **Verify on disk:** File exists at `Music/Tamil/<Year>/<Album>/<Title>.mp3`
6. **Verify ID3 tags:** Open the file in any tag editor — `TIT2`, `TPE1`, `TALB`, `TDRC`,
   `TCON`, `TXXX:PIPELINE_ID` should all be set. `APIC` (cover art) should be present if
   Shazam returned a cover URL.

---

### TC-02 — Collection-fix: filename contains `(From <Album>)` pattern

**Tests transition:** `pending → identified (collection-fix) → tagged → done`

1. Rename any MP3 to `SongTitle (From SomeAlbum).mp3` and place in `Input/Tamil/`.
2. Run Stage 1 only: `python3 main.py Input/Tamil/ --stage 1`
3. **Expected terminal output:**
   ```
   [max-XXXXXX] ✓ collection  (1/1) Tamil | SongTitle — SomeAlbum
   ```
4. **Verify in DB:** `status=identified`, `id_source=collection-fix`
5. Run stages 3+4: `python3 main.py --move`
6. **Verify on disk:** File exists at `Music/Tamil/Collections/SomeAlbum/SongTitle.mp3`

---

### TC-03 — Short file: under 8 seconds → no_match

**Tests transition:** `pending → no_match (short file)`

1. Place a file under 8 seconds in `Input/Tamil/`.
2. Run Stage 1: `python3 main.py Input/Tamil/ --stage 1`
3. **Expected terminal output:**
   ```
   [max-XXXXXX] ✗ no match  (1/1) Tamil | <filename>
   ```
4. **Verify in DB:** `status=no_match`, `error_msg` contains `too short for fingerprinting`

---

### TC-04 — No match: Shazam fails, no collection pattern

**Tests transition:** `pending → no_match`

1. Place an obscure or locally recorded MP3 in `Input/Tamil/` with a plain filename (no
   `From` pattern).
2. Run Stage 1: `python3 main.py Input/Tamil/ --stage 1`
3. **Expected terminal output:**
   ```
   [max-XXXXXX] ✗ no match  (1/1) Tamil | <filename>
   ```
4. **Verify in DB:** `status=no_match`, `id_source` is null

---

### TC-05 — Manual review: user enters metadata

**Tests transition:** `no_match → identified (manual entry) → tagged → done`

*Requires TC-04 to have run first — you need a `no_match` file in the DB.*

1. Run: `python3 main.py --review`
2. At the prompt for the `no_match` file, press `e`.
3. Enter: `Test Title | Test Artist | Test Album | 2001`
4. Confirm with `y`.
5. **Expected output:** `✓ Saved. Status → identified.`
6. Run: `python3 main.py --move`
7. **Verify on disk:** File exists at `Music/Tamil/2001/Test Album/Test Title.mp3`
8. **Verify ID3 tags:** `TIT2=Test Title`, `TPE1=Test Artist`, `TALB=Test Album`,
   `TDRC=2001`

---

### TC-06 — Manual review: partial override (fix year only)

**Tests transition:** `no_match → identified` with partial override syntax

*Requires a `no_match` file in the DB.*

1. Run: `python3 main.py --review`
2. For a song that already has Shazam title/artist (even if no_match — use a file that
   was partially identified), press `e`.
3. Enter: `| | | 1995` (leave all fields blank except year)
4. Confirm with `y`.
5. **Verify in DB:** `final_year=1995`, `final_title` and `final_artist` retain the
   existing values (not overwritten with empty strings).

---

### TC-07 — Review: skip and come back

**Tests:** `no_match` stays `no_match` after skip; resumed on next `--review`

1. Run: `python3 main.py --review`
2. Press `s` to skip the first file.
3. Press `q` to quit.
4. **Verify in DB:** `status` remains `no_match`; `last_attempt_at` is updated.
5. Run `python3 main.py --review` again — the same file should appear.

---

### TC-08 — Metadata search pass

**Tests transition:** `no_match → identified (metadata-search) → tagged → done`

*Requires a `no_match` file whose filename or ID3 tags contain a searchable title.*

1. Run: `python3 main.py --metadata-search`
2. Review the candidates shown for each file.
3. Pick `1` (or the correct candidate number) for one file.
4. **Expected output:** `✓ Accepted [1]. Status → identified.`
5. **Verify in DB:** `status=identified`, `id_source=metadata-search`
6. Run: `python3 main.py --move`
7. **Verify on disk:** File moved to the correct `Music/` path.

---

### TC-09 — AcoustID pass

**Tests transition:** `no_match → identified (acoustid) → tagged → done`

*Requires `ACOUSTID_API_KEY` set and `fpcalc` installed.*

1. Export the key: `export ACOUSTID_API_KEY=your_key_here`
2. Run: `python3 main.py --acoustid`
3. For a matched file, press `a` to accept.
4. **Verify in DB:** `status=identified`, `id_source=acoustid`
5. Run: `python3 main.py --move`
6. **Verify on disk:** File moved to `Music/` path.

---

### TC-10 — Duplicate detection

**Tests:** Duplicate song routed to `Duplicates/`; original `duplicate_count` incremented

*Requires at least one `done` song already in `Music/`.*

1. Place an audio file with identical content to a song already `done` in `Input/Tamil/`
   (copy the same MP3 with a different filename).
2. Run: `python3 main.py Input/Tamil/`
3. **Expected terminal output for Stage 4:**
   ```
   [max-XXXXXX] ⓪ duplicate  Tamil | <Title>
   ```
4. **Verify on disk:** File exists at `Music/Tamil/Duplicates/<Album>/<Title> (max-XXXXXX).mp3`
5. **Verify in DB:** Original song's `duplicate_count` has been incremented by 1.
6. Run `python3 main.py --review` and open the original song — it should show
   `⓪ 1 duplicate(s) in Music/Duplicates/`.

---

### TC-11 — Error recovery

**Tests transition:** `error → retry on next run`

1. Identify a song through Stage 1 so it has `status=identified`.
2. Manually set it to `error` in the DB:
   ```bash
   python3 -c "from pipeline.db import update_song; update_song('max-XXXXXX', status='error', error_msg='manual test')"
   ```
3. Run: `python3 main.py --move`
4. **Expected:** The song is retried. If the file exists and tags are valid, it should
   progress to `tagged` then `done`.
5. **Verify in DB:** `status=done`, `error_msg` cleared or updated.

---

### TC-12 — Dry run: no state changes

**Tests:** `--dry-run` produces no DB writes and no file moves

1. Ensure at least one `identified` song is in the DB.
2. Note the current file path and DB status.
3. Run: `python3 main.py Input/ --dry-run`
4. **Verify in DB:** Status of all songs is unchanged.
5. **Verify on disk:** No files were moved; `Input/` unchanged.
6. **Verify:** `Music/` folder was not modified.

---

### TC-13 — Resume safety: interrupt and re-run

**Tests:** Pipeline resumes correctly after interruption

1. Place 10+ files in `Input/Tamil/`.
2. Start Stage 1: `python3 main.py Input/Tamil/ --stage 1`
3. Press `Ctrl-C` after a few files are processed.
4. Note which files got `status=identified` or `no_match` in the DB.
5. Run Stage 1 again: `python3 main.py Input/Tamil/ --stage 1`
6. **Expected:** Already-processed files are skipped (`[SKIP] already in DB`). Only
   unprocessed files are sent to Shazam.
7. **Verify in DB:** No duplicate `song_id` entries; no regression in status for
   already-processed files.

---

### TC-14 — Renamed no_match file re-picked

**Tests:** When a `no_match` file is renamed and Stage 1 is re-run, the DB path is updated

1. Ensure a `no_match` song is in the DB (e.g. `Input/Tamil/Teeth.mp3`).
2. Rename the file: `mv Input/Tamil/Teeth.mp3 "Input/Tamil/pattu poove unnai paarthal.mp3"`
3. Run Stage 1: `python3 main.py Input/Tamil/ --stage 1`
4. **Expected terminal output:**
   ```
   [PATH]  path updated for max-XXXXXX: .../pattu poove unnai paarthal.mp3
   ```
5. **Verify in DB:** `file_path` for that `song_id` now points to the renamed file.
6. Run `--metadata-search` or `--acoustid` — the renamed file should be found and
   processed without a "file no longer exists" skip.

---

### TC-15 — `--review --flagged`: suspicious year detection

**Tests:** `--flagged` shows only songs with years outside 1940–present

1. Ensure at least one song in the DB has `shazam_year` or `final_year` set to an
   implausible value (e.g. manually set `shazam_year='1905'`).
2. Run: `python3 main.py --review --flagged`
3. **Expected:** Only the song(s) with bad years appear in the review queue.
4. Use the partial override to fix: `| | | 1995`
5. **Verify in DB:** `final_year=1995`; original `shazam_year=1905` unchanged (override
   is stored in `final_year`, not `shazam_year`).

---

### TC-16 — `--stats` output

**Tests:** `--stats` accurately reports counts across statuses and languages

1. After running several of the above tests, run: `python3 main.py --stats`
2. **Verify:** Status counts match what you know to be in the DB from the tests above.
3. **Verify:** Language breakdown matches the languages of files processed.
4. **Verify:** Top albums list is populated and contains no blank entries.

---

### TC-17 — `--zeroise` confirmation guard

**Tests:** `--zeroise` requires explicit `YES`; any other input aborts

1. Run: `python3 main.py --zeroise`
2. Type anything other than `YES` (e.g. `yes`, `y`, `no`, blank).
3. **Expected output:** `Aborted.` — DB is unchanged.
4. Run again and type `YES` exactly.
5. **Expected:** All rows deleted.
6. Run `python3 main.py --stats` — all counts should be 0.

---

### TC-18 — `--move` operates without a source path

**Tests:** `--move` tags and moves all `identified` songs without needing `Input/`

1. Run Stage 1 on a folder to get some `identified` songs.
2. Run: `python3 main.py --move` (no source path argument)
3. **Expected:** Stages 3 and 4 run on all `identified` songs; files land in `Music/`.
4. **Verify:** No error about missing source path.

---

### TC-19 — `--move --dry-run`: preview with no changes

**Tests:** `--move --dry-run` previews without writing tags or moving files

1. Ensure at least one `identified` song is in the DB.
2. Run: `python3 main.py --move --dry-run`
3. **Expected:** Output shows what would be tagged/moved, but DB status is unchanged
   and no files are moved.

---

### TC-20 — `--review --folder`: scope review to a specific folder path

> **Status:** Pending implementation — tracked in issue #15.
> Found during TC-02 system testing (2026-04-02): when correcting metadata for songs in a
> specific output folder (e.g. `Music/Tamil/Collections/`), the user needs to filter the
> review queue by folder rather than reviewing the entire queue.

**Tests:** `--review --folder` filters queue to songs matching a path prefix

1. Ensure songs exist in both `Music/Tamil/Collections/` and `Music/Tamil/<Year>/`.
2. Run: `python3 main.py --review --all --folder=Music/Tamil/Collections/`
3. **Expected:** Only songs whose `file_path` or `final_path` starts with
   `Music/Tamil/Collections/` appear in the review queue.
4. **Verify:** Songs from `Music/Tamil/<Year>/` do not appear.
5. Run: `python3 main.py --review --all --folder=Music/Tamil/` — should include all Tamil songs.
6. Run with a folder that matches nothing — should print a clean "no songs found" message
   and exit without error.
7. Verify `--folder` combines correctly with `--flagged` and `--limit N`.

---

## Full regression checklist

After completing all test cases above, verify:

- [ ] All statuses represented: `pending`, `identified`, `tagged`, `done`, `no_match`, `error`
- [ ] All three output paths used: standard `Music/<Lang>/<Year>/<Album>/`, `Collections/`, `Duplicates/`
- [ ] All three `id_source` values confirmed: `shazam`, `collection-fix`, `metadata-search` (or `acoustid`)
- [ ] `meta_before` and `meta_after` populated in DB for tagged songs
- [ ] `duplicate_count` incremented correctly for duplicate songs
- [ ] `runs/` folder contains a timestamped subfolder with `run.log` and `summary.json`
- [ ] `summary.json` fields match observed counts
- [ ] No file in `Input/` has been deleted (only moved to `Music/`)
- [ ] No orphaned files in `Music/` (every file there corresponds to a `done` DB row)

---

## Links

[README.md](../../README.md) | [Architecture](../engineering/ARCHITECTURE.md) | [User Guide](../guide/USER_GUIDE.md) | [Database Reference](../engineering/DATABASE.md)
