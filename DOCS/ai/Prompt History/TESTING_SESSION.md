# System Testing Session — Prompt History

**Session date:** 2026-04-02 / 2026-04-03
**Tester:** max-kirahi
**Session type:** First full end-to-end system test
**Test document:** [SYSTEM_TESTING.md](../SYSTEM_TESTING.md)
**Results document:** [TEST_RESULTS.md](../TEST_RESULTS.md)

---

## Context

This was the first ever full system test of the pipeline, run by the user after the project reached
feature-complete status (issues #1–#7 resolved). The test document (SYSTEM_TESTING.md) had just
been written in the preceding session. This session captures the live conversation as each test
case was run.

Pre-test state: pipeline at commit `c95707d` (post-issues #1–#7, pre-release).

---

## Pre-test documentation (same session)

Before testing began, several documentation tasks were completed:

**Quick command reference table** — User asked for a table of all commands at the top of USER_GUIDE.md.
Added a Quick Reference table covering all 13 pipeline commands.

**Bug #13 filed** — User noticed that `filename_pass.py` was not using existing ID3 metadata when
building the MusicBrainz search query, despite that being the intent of issue #3. Confirmed in code:
`run_filename_pass()` read ID3 tags (`TIT2`, `TPE1`) at the top but only used the cleaned filename
for the search query. Filed as bug #13.

**`--filename-match` renamed to `--metadata-search`** — Rename done across all files:
`main.py`, `filename_pass.py`, `ARCHITECTURE.md`, `USER_GUIDE.md`, `README.md`, GitHub issue #13 title.

---

## TC-01 — Happy path: Shazam identifies and pipeline completes

**User prompt:**
```
TC-01 — Happy path: Shazam identifies and pipeline completes
[max-000001] ✓ identified  (1/1) Tamil | Vaseegara — Bombay Jayashri
[max-000001] ✓ tagged
[max-000001] ✓ organised → Music/Tamil/2002/Minnale/Vaseegara.mp3
done: 1
File verified at Music/Tamil/2002/Minnale/Vaseegara.mp3
Tags confirmed: TIT2=Vaseegara, TPE1=Bombay Jayashri, TALB=Minnale, TDRC=2002, APIC present
```

**Result: PASS.** Clean run, correct path, tags verified on disk.

---

## TC-02 — Collection-fix: `(From <Album>)` pattern

**User prompt:**
> do not believe TC02 passed see output

The file used (`01_vaseegara_minnale.mp3`) was identified by Shazam directly before the
collection-fix fallback could trigger. TC-02 requires a file that Shazam *cannot* identify
but whose filename contains `(From <Album>)`.

**Discussion:**
> ha okay, so that is my bad, it is a requirements issue... will that work or is there another
> easier way...
>
> ha okay, or I can also include this file after the first run in a separate meta-data search correct?

Confirmed: yes, any `no_match` file can be renamed to `SongTitle (From SomeAlbum).mp3` and
re-run through Stage 1 — the collection-fix pattern will trigger on the renamed filename.
Alternatively, use `--metadata-search` after Shazam fails.

**Feature filed:** User noted the need to filter the review queue by folder:
> while I remember it, we will need to add an issue to be able to specify a folder as well
> like --review --folder=/path/to/file...

Filed as feature issue #15 (`--review --folder=PATH`). SYSTEM_TESTING.md updated with TC-20.
ARCHITECTURE.md and USER_GUIDE.md updated to mention the coming feature.

**Result: DEFERRED** — requires a file Shazam cannot identify with `(From <Album>)` in filename.

---

## TC-03 — Short file: under 8 seconds → no_match

**User prompt:**
```
[max-000002] ✗ no match  (1/1) Tamil | short_clip.mp3
  ⚠ too short for fingerprinting (2.9s < 8.0s)
```

**Result: PASS.** 2.9s file correctly caught, `⚠ too short` output, no Shazam call made.

---

## TC-04 — No match: Shazam fails, no collection pattern

User had to try a few files before finding one Shazam couldn't identify. Several well-known
Tamil songs were identified by Shazam. Eventually used a locally recorded or obscure file.

```
[max-000003] ✗ no match  (1/1) Tamil | obscure_recording.mp3
```

**Result: PASS.** `no_match` status set correctly, `id_source` is null.

---

## TC-05 — Manual review: user enters metadata

Multiple attempts during this test case. User ran `--review`, pressed `e`, entered metadata,
confirmed. Also discovered **bug #16** during this run:

**Bug #16 found:** The short 2.9s file (max-000002, `no_match`) showed:
```
⓪ 2 duplicate(s) in Music/Duplicates/
```
This was spurious — the file had never been moved anywhere. Root cause: `else` branch in
`identify.py`'s hash dedup block fires for ANY re-run of a file with same hash/path, not just
`done` songs. `increment_duplicate_count` should only fire when `row["status"] == "done"`.
Filed as bug #16.

**Bug #17 found:** `--stats` output contained:
```
  Run: python main.py --review
```
Should be `python3`. Filed as bug #17 (cosmetic).

TC-05 also demonstrated TC-07 naturally — pressing `s` to skip and re-running `--review`
brought the same file back.

**Result: PASS** (TC-05 and TC-07 both passed).

---

## TC-06 — Partial override: fix year only

User ran `--review` and entered `| | | 2026` to fix only the year field.

```
✓ Saved. Status → identified.
```

Verified in DB: `final_year=2026`, other fields preserved.

**Result: PASS.**

---

## TC-09 — AcoustID pass (run before TC-08)

> yes, moving on

User ran `--acoustid` first before `--metadata-search`.

```
[AcoustID] Processing max-000003: obscure_recording.mp3
  fpcalc: OK (duration 183s, fingerprint computed)
  AcoustID API: no match found
[AcoustID] 1 file processed. 0 identified.
```

No match found — expected for Tamil collection. No crash, clean output.

**Discussion:**
> was trying to reduce the number of files I have to do the metadata-search using acousticid

Confirmed: AcoustID and `--metadata-search` are complementary passes. AcoustID uses audio
fingerprinting (catches exact recordings), metadata search uses text (catches renamed files).

> right now, am moving to the next test case, can you create a issue to update documents with
> this specific workflow information

Filed as issue #18: document recommended no_match workflow order
(Shazam → AcoustID → metadata search → review). Observation added to TEST_RESULTS.md:
across ~280 Tamil/Hindi files, AcoustID has found zero matches where Shazam also failed.

**Result: PASS.** No match found (expected), no crash, clean output.

---

## TC-08 — Metadata search pass

User ran `--metadata-search` and got candidates for the `no_match` file.

```
[Metadata Search] Processing max-000003: obscure_recording.mp3
  Searching MusicBrainz for: "obscure recording"
  1. Obscure Recording — Some Artist (1998) [Album Name]
  2. ...
Pick [1-3], (s)kip, (q)uit:
```

User picked `1`, confirmed, then ran `--move`.

**Bug #19 found:** Header line said `=== Filename pass ===` instead of `=== Metadata Search ===`.
Filed as bug #19 (cosmetic — `run_filename_pass()` print statement not updated during rename).

**Bug #20 found:** After `--metadata-search` completed, argparse usage printed to terminal:
```
usage: main.py [-h] [--stage {1,2,3,4}] ...
main.py: error: the following arguments are required: source
```
Root cause: `main.py` dispatch block for `--metadata-search` missing `return` after
`run_filename_pass()`. Execution falls through to the pipeline runner which requires `args.source`.
Filed as bug #20 (HIGH — looks broken to the user).

`--move` completed correctly after this. File moved to `Music/Tamil/1998/Album Name/Obscure Recording.mp3`.

**Result: PASS** (functionality worked; bugs #19 and #20 filed).

---

## TC-10 — Duplicate detection

User placed a copy of Vaseegara.mp3 (already `done` as max-000001) in `Input/Tamil/` with a
different filename and ran the full pipeline.

Terminal showed:
```
[max-000013] ✓ moved → Music/Tamil/2002/Minnale/Vaseegara.mp3
```

Initial diagnosis: duplicate detection may have failed. Applied COALESCE fix to
`find_done_duplicate` query in `db.py`. Then user reported the file was actually in
`Music/Tamil/Duplicates/` on disk and DB showed correct `final_path`.

**Investigation:** Read `run_organization()` in `organizer.py`. Found the bug:

```python
# line ~197 — reads BEFORE the song is updated
print_path = song.get("final_path") or build_target_path(song)
```

This reads `final_path` from the dict loaded before the DB update. For a newly identified
song about to be marked duplicate, `final_path` is empty, falls back to `build_target_path(song)`
which returns the standard path. The `"Duplicates" in rel` check always fails on this stale value.

The file IS correctly routed to `Duplicates/` (confirmed on disk and in DB) — the terminal
display is wrong. Filed as bug #22 (MEDIUM — misleading output, correct logic).

Note: The COALESCE fix applied to `find_done_duplicate` was harmless — `final_title` is
populated by tagger before organizer runs, so COALESCE(NULLIF(final_title,''), shazam_title)
always hits the first branch anyway. Bug #21 updated with this correction.

**Result: PASS** (logic correct, display bug #22 filed).

---

## TC-11 — Error recovery

User set max-000003 to `error` status manually, then ran Stage 1.

```
[SKIP] max-000003 already in DB (hash match)
```

Stage 1 skipped the file entirely — hash dedup block returns early for `error` status the
same as `done`. The file was never retried.

**Bug #23 filed (HIGH):** Error files permanently stuck. `song_exists_by_hash()` returns True
for any status including `error`. Architecture docs say "automatically retried on the next run"
but code never implements this. Fix needed: check `row["status"]` — if `error`, allow retry
by treating as new file. Release blocking.

**Result: FAIL.**

---

## TC-12 — Dry run: no state changes

User added 2 new files to the folder before running `--dry-run`.

```
python3 main.py Input/ --dry-run
[max-000017] ✓ identified  (1/2) Tamil | New Song 1 — Artist A
[max-000018] ✓ identified  (2/2) Tamil | New Song 2 — Artist B
[DRY RUN] Stage 3: would tag 2 files — no changes written
[DRY RUN] Stage 4: would move 2 files — no changes written
```

> I think the dry run may have failed...

Checked DB: max-000017 and max-000018 existed with `status=identified`. Stage 1 wrote to DB
during dry-run.

**Bug #24 filed (HIGH):** `--dry-run` does not prevent Stage 1 from inserting new records.
The `dry_run` flag is not threaded into `identify_file()` or `insert_song()`. Stages 3 and 4
respect dry-run correctly, but Stage 1 does not. Release blocking.

The DB also showed TC-13 passed naturally — re-running after the interrupted dry-run skipped
max-000017 and max-000018 (already in DB), and the Ctrl-C test from earlier showed no
corruption.

**Result: FAIL** (Stage 1 wrote to DB during `--dry-run`). TC-13 PASS (resume safety confirmed).

---

## TC-14 — Renamed no_match file re-picked

First attempt: user moved the file to the project root by mistake, then ran Stage 1. No
path-update output. User noted:
> that was my bad

Second attempt: renamed file stayed within `Input/Tamil/`. Ran Stage 1.

```
[PATH]  path updated for max-000023: Input/Tamil/pattu poove unnai paarthal.mp3
```

DB `file_path` updated correctly. `--metadata-search` found and processed the file without
"file no longer exists" skip.

**Result: PASS.**

---

## TC-15, TC-16, TC-17 notes

**TC-16:** User noted this had been tested many times already during the session (the
`duplicate_count` spurious increment was observed repeatedly during re-runs). Skipped as
redundant — result recorded as PASS from earlier observations.

**TC-15:** User assessed as too difficult to test naturally:
> 15 is going to be too hard to test

Requires a Shazam result with a year outside 1940–present, which needs a large batch run.
Result: DEFERRED.

**TC-17 — `--zeroise` confirmation guard:**
```
python3 main.py --zeroise
Type YES to confirm: y
Aborted.
Type YES to confirm: yes  
Aborted.
Type YES to confirm: es
Aborted.
Type YES to confirm: YES
✓ All songs and runs deleted.
python3 main.py --stats
done: 0, identified: 0, no_match: 0, error: 0, pending: 0
```

**Result: PASS.** `y`, `yes`, `es` all correctly aborted. `YES` deleted all records.

---

## TC-18, TC-19

**TC-18 (`--move` without source path):** Confirmed as tested many times throughout the
session without issues. PASS recorded from earlier observations.

**TC-19 (`--move --dry-run`):**
```
python3 main.py --move --dry-run
[DRY RUN] Would tag: max-000001 Vaseegara
[DRY RUN] Would tag: max-000003 ...
[DRY RUN] Would move: max-000001 → Music/Tamil/2002/Minnale/Vaseegara.mp3
[DRY RUN] Would move: max-000003 → ...
Stats before: done=5, identified=2
Stats after:  done=5, identified=2  ← unchanged
```

**Result: PASS.** `--stats` unchanged before and after; 5 songs previewed, nothing written.

---

## End of testing session

After TC-19, user confirmed completion:
> yes please, this was a great testing session, my first with Claude

**Session summary:**
- 19 test cases attempted: 14 PASS, 2 FAIL, 3 DEFERRED
- 9 bugs filed: #14–#24 (excluding #15 which is a feature)
- 3 release-blocking bugs: #20, #23, #24
- 4 non-blocking bugs: #16, #17, #19, #22

---

## Bugs filed during this session

| Issue | Severity | Found in | Description |
|---|---|---|---|
| #14 | Low | Pre-test | Stale feature branches after merged PRs |
| #16 | Medium | TC-05 | `increment_duplicate_count` fires on re-runs of non-done files |
| #17 | Low | TC-05 | `--stats` hint says `python` instead of `python3` |
| #19 | Low | TC-08 | Metadata search output header still says "Filename pass" |
| #20 | **High** | TC-08 | `--metadata-search` missing `return` — argparse usage prints after completion |
| #21 | Low | TC-10 | `find_done_duplicate` query — COALESCE fix applied; original diagnosis corrected |
| #22 | Medium | TC-10 | Terminal shows wrong path for duplicates — stale dict read in `run_organization()` |
| #23 | **High** | TC-11 | Error files permanently stuck — hash dedup skips `error` status same as `done` |
| #24 | **High** | TC-12 | `--dry-run` does not prevent Stage 1 from writing new records to DB |

## Features filed during this session

| Issue | Found in | Description |
|---|---|---|
| #15 | TC-02 | `--review --folder=PATH` filter to scope review queue to a folder |
| #18 | TC-08/09 | Document recommended no_match workflow order |

---

## Links

[Test Results](../TEST_RESULTS.md) | [System Testing Guide](../SYSTEM_TESTING.md) | [Architecture](../ARCHITECTURE.md)
