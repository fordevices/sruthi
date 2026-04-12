# Database Reference

## Overview

State is stored in a single SQLite file: `music.db`. It uses WAL journal mode for
durability. There are two tables: `songs` (one row per MP3 file ever discovered) and
`runs` (one row per pipeline invocation).

**Never edit `music.db` directly.** All reads and writes go through functions in
`pipeline/db.py`. Never run raw `UPDATE` or `DELETE` against the live database from the
command line — if you need to inspect it, use read-only `SELECT` queries only.

To clear the database completely (e.g. between test runs), use the safe CLI command:

```bash
python3 main.py --zeroise
```

This will ask you to type `YES` before deleting anything.

---

## Table: `songs`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment internal row ID |
| `song_id` | TEXT UNIQUE | Human-readable ID: `max-000001` pattern |
| `file_path` | TEXT | Original absolute path at time of discovery |
| `file_hash` | TEXT | MD5 of file bytes — used for dedup and resume |
| `language` | TEXT | Taken from Input subfolder name (Tamil / Hindi / etc.) |
| `status` | TEXT | `pending` → `identified` → `no_match` → `tagged` → `done` → `error` |
| `shazam_title` | TEXT | Title returned by ShazamIO |
| `shazam_artist` | TEXT | Artist returned by ShazamIO |
| `shazam_album` | TEXT | Album returned by ShazamIO |
| `shazam_year` | TEXT | Year returned by ShazamIO |
| `shazam_genre` | TEXT | Genre returned by ShazamIO |
| `shazam_cover_url` | TEXT | Cover art URL returned by ShazamIO |
| `final_title` | TEXT | Title actually written to tags (after any override) |
| `final_artist` | TEXT | Artist actually written to tags |
| `final_album` | TEXT | Album actually written to tags |
| `final_year` | TEXT | Year actually written to tags |
| `final_genre` | TEXT | Genre actually written to tags |
| `final_path` | TEXT | Absolute path after Stage 4 rename + move |
| `override_used` | INTEGER | 1 if user manually entered metadata, 0 otherwise |
| `override_raw` | TEXT | Raw string the user typed during manual review |
| `run_id` | TEXT | Timestamp of the run that last touched this row |
| `created_at` | TEXT | ISO timestamp — when first discovered |
| `updated_at` | TEXT | ISO timestamp — last status change |
| `error_msg` | TEXT | Last error message if status = `error` |
| `meta_before` | TEXT | JSON snapshot of ID3 tags in the file before Stage 3 wrote new ones |
| `meta_after` | TEXT | JSON snapshot of the tag values actually written by Stage 3 |
| `duplicate_count` | INTEGER | Number of duplicate files found for this entry (set by issue #5) |
| `id_source` | TEXT | Which mechanism identified this file: `shazam`, `shazam-multiprobe`, `acrcloud`, `metadata-search`, `collection-fix` |
| `last_attempt_at` | TEXT | ISO timestamp of the most recent identification attempt |

---

## Table: `runs`

| Column | Type | Description |
|---|---|---|
| `run_id` | TEXT PK | Timestamp string e.g. `2026-03-21_14-32-00` |
| `started_at` | TEXT | ISO timestamp |
| `finished_at` | TEXT | ISO timestamp (null until run completes) |
| `mode` | TEXT | `single` or `folder` |
| `source_path` | TEXT | File or folder that was processed |
| `files_total` | INTEGER | Total MP3s found |
| `files_done` | INTEGER | Successfully completed (status = done) |
| `files_error` | INTEGER | Errors encountered |
| `files_no_match` | INTEGER | Files ShazamIO could not identify |

---

## Song ID format

Pattern: `max-XXXXXX` (six zero-padded digits)

- Generated at insert time, before any API calls
- Reads the current `MAX(song_id)` from the songs table, parses the number, increments by 1
- First file ever processed: `max-000001`
- Stored permanently in the ID3 tag `TXXX:PIPELINE_ID` so the ID survives file renames
  and moves — you can always match a physical file back to its DB row

---

## Status flow

```
[file discovered]
      │
      ▼
  pending ──► identified ──► tagged ──► done
                  │
                  ▼
              no_match ──► (manual review) ──► identified ──► tagged ──► done
                  │
                  └──► (user skips) ──► no_match (stays, processed next --review)

  any stage can go to ──► error  (retried on next run)
```

| Status | Set by | Meaning | Next step |
|---|---|---|---|
| `pending` | `db.insert_song()` | File found, not yet fingerprinted | Stage 1 processes it |
| `identified` | `identify.py` or `review.py` | Shazam matched, or user entered metadata | Stage 3 tags it |
| `no_match` | `identify.py` | Shazam could not identify file | `--review` to enter manually |
| `tagged` | `tagger.py` | ID3 tags written into file | Stage 4 moves it |
| `done` | `organizer.py` | File moved to `Music/` structure | Nothing — complete |
| `error` | any stage | Something failed | Automatically retried on next run |

---

## Field priority rule

When writing ID3 tags (Stage 3) and building output paths (Stage 4), fields are resolved
in this order:

```
final_*  (non-empty after strip)  →  use it
shazam_* (non-empty after strip)  →  use it
otherwise                         →  fallback ("Unknown Year", "Unknown Album", etc.)
```

`final_*` fields are set either by Stage 1 (seeded directly from Shazam at identify time)
or overwritten by Stage 2 (manual review). A `final_*` value always wins because it
reflects any human correction that has been applied.

`shazam_*` fields are exactly what ShazamIO returned — unmodified.

Never write an empty string into an ID3 text frame — omit the tag entirely if the
resolved value is empty.

The `resolve()` function in `tagger.py` implements this rule and is also imported by
`organizer.py` — both stages use the identical priority logic.

---

## Persistence and interruption safety

`music.db` is a file on disk. It is never wiped, never reset, and never touched by closing
a terminal window or Ctrl-C. It accumulates permanently across every run, every session,
and every restart.

| Interruption | What happens | Recovery |
|---|---|---|
| Ctrl-C mid-Stage 1 | Files before interruption are `done` or `no_match` in DB | Re-run — processed files skipped by MD5 hash |
| Ctrl-C mid-Stage 3 | Interrupted file stays `identified` — tag may be partial | Re-run `--stage 3` — file is re-tagged cleanly |
| Ctrl-C mid-Stage 4 | Interrupted file stays `tagged` — file may or may not have moved | Re-run `--stage 4` — move is retried |
| Terminal closed | Identical to Ctrl-C — DB is not affected | Re-run same command |
| `error` status | Stage failed for this file | Automatically retried on next run |
| `no_match` status | Shazam could not identify file | Held until `--review` |

For a 1000-file collection at the default 2-second sleep, a full Stage 1 run takes ~33 minutes.
You can run it overnight, interrupt at any point, and resume the next day. Only unprocessed
files are touched.

To check progress at any time without running anything:

```bash
python3 main.py --stats
```

---

## Querying the database directly

These are safe read-only queries you can run against `music.db`:

```sql
-- See everything that still needs review
SELECT song_id, language, file_path FROM songs WHERE status='no_match';
```

```sql
-- See all done songs with their final paths
SELECT song_id, language, final_title, final_artist, final_path
FROM songs WHERE status='done' ORDER BY language, final_year;
```

```sql
-- See runs history
SELECT run_id, source_path, files_total, files_done, files_no_match,
       duration_sec FROM runs ORDER BY started_at DESC;
```

Run these via:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('music.db')
conn.row_factory = sqlite3.Row
for row in conn.execute('SELECT song_id, language, status FROM songs LIMIT 10'):
    print(dict(row))
"
```

---

## Links

[README.md](../README.md) | [Architecture](ARCHITECTURE.md)
