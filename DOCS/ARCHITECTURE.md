# Architecture

## What Sruthi does, in one sentence

Walk a folder of MP3s → identify each one by audio fingerprint → write correct ID3 tags → move to `Music/<Language>/<Year>/<Album>/`.

---

## The four stages

Every run executes these stages in order. Each stage only processes songs in the right state — so stopping and re-running is always safe.

| Stage | What it does | Input state | Output state |
|---|---|---|---|
| 1 — Identify | Fingerprint each file via Shazam; fall back to filename pattern detection | `pending` | `identified` or `no_match` |
| 2 — Review | Interactive terminal review for unmatched files (skipped in batch mode) | `no_match` | `identified` (manual) |
| 3 — Tag | Write ID3 tags (title, artist, album, year, genre, cover art) via Mutagen | `identified` | `tagged` |
| 4 — Organise | Move file to `Music/<Language>/<Year>/<Album>/`; detect and route duplicates | `tagged` | `done` |

---

## Optional identification passes

These run independently — after Stage 1 — against songs already in the database with `no_match` status. Each one that finds a match sets `status='identified'`. Run `--move` afterwards to execute Stages 3 and 4.

| Pass | Command | How it works | Best for |
|---|---|---|---|
| Multi-probe | `--multiprobe` | Re-probes Shazam at 4 time positions (15/35/55/75% of duration) instead of one | Songs Shazam missed due to a quiet intro |
| ACRCloud | `--acrcloud` | Audio fingerprint against ACRCloud's Recorded Music database (includes Saregama/HMV India catalog) | Pre-2000 Tamil and Hindi film music absent from Shazam |
| Metadata search | `--metadata-search` | Reads existing ID3 tags or cleaned filename; searches iTunes; interactive candidate review | Any song with a meaningful filename or partial tags |

---

## Status flow

```
[file discovered]
      │
      ▼
  pending
      │
      ├── Shazam match ─────────────────────────────► identified  (id_source='shazam')
      ├── filename has "from <Album>" pattern ───────► identified  (id_source='collection-fix')
      └── no match ──────────────────────────────────► no_match
                │
                ├── --multiprobe hit ───────────────► identified  (id_source='shazam-multiprobe')
                ├── --acrcloud hit ─────────────────► identified  (id_source='acrcloud')
                ├── --metadata-search accepted ─────► identified  (id_source='metadata-search')
                ├── --review manual entry ──────────► identified  (override_used=1)
                └── still no result ────────────────► no_match   (stays, retry later)

  [unhandled exception in Stage 1] ────────────────► error       (auto-retried on next run)

                              identified
                                   │
                             Stage 3 — tag
                                   │
                                tagged
                                   │
                             Stage 4 — organise
                             │          │           │
                           done       done        done
                        (standard) (Collections/) (Duplicates/)
```

Additional terminal states:

| Status | Meaning |
|---|---|
| `removed` | File was deleted from disk; marked by `--mark-removed` or manual DB update |
| `error` | Unhandled exception; automatically reset to `pending` on the next run |

---

## Module map

```
sruthi/
├── main.py                     CLI entry point — argparse only, no business logic
├── gui.py                      Streamlit NL query GUI (read-only)
└── pipeline/
    ├── config.py               All constants and env vars (single source of truth)
    ├── db.py                   All SQLite operations (no other module runs raw SQL)
    ├── runner.py               Orchestrator — ties stages together, writes run log + summary.json
    ├── identify.py             Stage 1 — ShazamIO fingerprint + collection-fix fallback
    ├── review.py               Stage 2 — interactive manual review CLI
    ├── tagger.py               Stage 3 — Mutagen ID3 tag write + cover art download
    ├── organizer.py            Stage 4 — rename, move, duplicate detection
    ├── collection.py           Collection-fix pattern extraction (shared utility)
    ├── multiprobe_pass.py      --multiprobe pass
    ├── acrcloud_pass.py        --acrcloud pass
    ├── filename_pass.py        --metadata-search pass
    └── transliterate.py        --transliterate pass (Sarvam AI)
```

**Key design rules:**
- `db.py` is the only file that runs SQL. Everything else calls named functions.
- `main.py` contains no business logic — it only parses arguments and routes.
- Stages are strictly ordered: `identify.py` never imports from `tagger.py` or `organizer.py`.
- `config.py` is imported by every module; nothing else imports from `runner.py` except ANSI colour constants.

---

## Database

State lives entirely in `music.db` (SQLite). Key columns:

| Column | Purpose |
|---|---|
| `song_id` | Stable identifier (`max-000001`), never changes even if file is renamed |
| `file_hash` | MD5 of file content — deduplication key |
| `file_path` | Current path on disk (updated if file is renamed) |
| `language` | Inferred from `Input/<Language>/` folder name |
| `status` | `pending → identified → tagged → done` (or `no_match / error / removed`) |
| `id_source` | Which pass identified this song (`shazam`, `acrcloud`, `metadata-search`, etc.) |
| `final_path` | Absolute path after Stage 4 move |
| `meta_before` | JSON snapshot of ID3 tags before Stage 3 wrote them (audit trail) |
| `meta_after` | JSON snapshot of values actually written by Stage 3 |

Schema migrations run automatically at startup via `PRAGMA table_info` + `ALTER TABLE` — no manual steps needed when upgrading.

Full schema: [DATABASE.md](DATABASE.md)

---

## Resume safety

Every file is identified by MD5 hash when first seen. On re-run:
- `done` → skipped instantly
- `identified` / `tagged` → skipped (picked up by the next stage)
- `no_match` → skipped by Stage 1; eligible for optional passes
- `error` → reset to `pending` and retried
- `pending` → retried (was in-flight when the previous run crashed)

This means stopping mid-run with Ctrl-C and re-running the same command is always safe.

---

## Output structure

```
Music/<Language>/<Year>/<Album>/<Title> - <Artist>.mp3      ← standard
Music/<Language>/Collections/<Album>/<Title>.mp3            ← collection-fix (no year)
Music/<Language>/Duplicates/<Album>/<Title> (song_id).mp3   ← duplicate of existing done song
```

Missing field fallbacks: no year → `Unknown Year`, no album → `Unknown Album`, no title → `<song_id>`.

Illegal filename characters (`/ \ : * ? " < > |`) are replaced with `_`. Tamil and Hindi script, brackets, ampersands, and hyphens are preserved.

---

## Run logging

Every invocation creates a timestamped folder under `runs/`:

```
runs/2026-04-17_18-01-10/
    run.log         Full console output
    summary.json    Machine-readable stats (files_total, identified, no_match, errors, duration_sec)
```

---

## Links

[README](../README.md) | [User Guide](USER_GUIDE.md) | [Database Reference](DATABASE.md) | [Design Decisions](DESIGN_DECISIONS.md)
