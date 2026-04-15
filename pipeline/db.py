"""
Sruthi — database access layer
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Single source of truth for all reads and writes to music.db. Creates the
schema on first connect and applies additive column migrations automatically
so existing databases are never broken by upgrades.

Tables:
  songs                  — one row per MP3, tracks status through all pipeline stages
  runs                   — one row per pipeline run, summary stats written at finish
  artist_transliterations — cache for Sarvam AI transliteration results (issue #26)

Status lifecycle:
  pending → identified → tagged → done
           ↘ no_match (held for manual review)
           ↘ error    (retried on next run)
           ↘ removed  (file manually deleted; excluded from all passes)

Docs:
  Full schema and field descriptions — DOCS/DATABASE.md
  Pipeline stage overview            — DOCS/ARCHITECTURE.md
"""

import sqlite3
from datetime import datetime, timezone

from pipeline import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS songs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id         TEXT UNIQUE,
            file_path       TEXT,
            file_hash       TEXT,
            language        TEXT,
            status          TEXT,
            shazam_title    TEXT,
            shazam_artist   TEXT,
            shazam_album    TEXT,
            shazam_year     TEXT,
            shazam_genre    TEXT,
            shazam_cover_url TEXT,
            final_title     TEXT,
            final_artist    TEXT,
            final_album     TEXT,
            final_year      TEXT,
            final_genre     TEXT,
            final_path      TEXT,
            override_used   INTEGER,
            override_raw    TEXT,
            run_id          TEXT,
            created_at      TEXT,
            updated_at      TEXT,
            error_msg       TEXT,
            meta_before     TEXT,
            meta_after      TEXT,
            duplicate_count INTEGER,
            id_source       TEXT,
            last_attempt_at TEXT
        );

        CREATE TABLE IF NOT EXISTS artist_transliterations (
            roman_name   TEXT NOT NULL,
            language     TEXT NOT NULL,
            native_name  TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            PRIMARY KEY (roman_name, language)
        );

        CREATE TABLE IF NOT EXISTS runs (
            run_id        TEXT PRIMARY KEY,
            started_at    TEXT,
            finished_at   TEXT,
            mode          TEXT,
            source_path   TEXT,
            files_total   INTEGER,
            files_done    INTEGER,
            files_error   INTEGER,
            files_no_match INTEGER
        );
    """)
    conn.commit()

    # Migrate existing databases that predate these columns.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    migrations = {
        "meta_before":     "ALTER TABLE songs ADD COLUMN meta_before     TEXT",
        "meta_after":      "ALTER TABLE songs ADD COLUMN meta_after      TEXT",
        "duplicate_count": "ALTER TABLE songs ADD COLUMN duplicate_count INTEGER",
        "id_source":       "ALTER TABLE songs ADD COLUMN id_source       TEXT",
        "last_attempt_at": "ALTER TABLE songs ADD COLUMN last_attempt_at TEXT",
    }
    for col, stmt in migrations.items():
        if col not in existing:
            conn.execute(stmt)
    conn.commit()

    return conn


def generate_song_id() -> str:
    conn = get_connection()
    try:
        row = conn.execute("SELECT MAX(song_id) FROM songs").fetchone()
        max_val = row[0]
        if max_val is None:
            return "max-000001"
        number = int(max_val.split("-")[1])
        return f"max-{number + 1:06d}"
    finally:
        conn.close()


def insert_song(file_path: str, file_hash: str, language: str, run_id: str) -> str:
    song_id = generate_song_id()
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO songs
                (song_id, file_path, file_hash, language, status, run_id, created_at, updated_at)
            VALUES
                (?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (song_id, file_path, file_hash, language, run_id, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return song_id


def update_song(song_id: str, **kwargs) -> None:
    kwargs["updated_at"] = _now()
    columns = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [song_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE songs SET {columns} WHERE song_id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_songs_by_status(status: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM songs WHERE status = ?", (status,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_songs() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM songs ORDER BY song_id"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def song_exists_by_hash(file_hash: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM songs WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def create_run(run_id: str, mode: str, source_path: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO runs (run_id, started_at, mode, source_path)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, _now(), mode, source_path),
        )
        conn.commit()
    finally:
        conn.close()


def finish_run(
    run_id: str,
    files_total: int,
    files_done: int,
    files_error: int,
    files_no_match: int,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, files_total = ?, files_done = ?,
                files_error = ?, files_no_match = ?
            WHERE run_id = ?
            """,
            (_now(), files_total, files_done, files_error, files_no_match, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def find_done_duplicate(title: str, artist: str, language: str) -> dict | None:
    """
    Return the first done song with matching title+artist+language, or None.
    Comparison is case-insensitive and whitespace-trimmed.
    Used by organizer.py to detect duplicate songs before moving.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT * FROM songs
               WHERE status = 'done'
               AND LOWER(TRIM(COALESCE(NULLIF(final_title,''),  shazam_title,  ''))) = LOWER(TRIM(?))
               AND LOWER(TRIM(COALESCE(NULLIF(final_artist,''), shazam_artist, ''))) = LOWER(TRIM(?))
               AND LOWER(language) = LOWER(?)
               ORDER BY created_at ASC LIMIT 1""",
            (title, artist, language),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def increment_duplicate_count(song_id: str) -> None:
    """Increment duplicate_count by 1 for the given song."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE songs
               SET duplicate_count = COALESCE(duplicate_count, 0) + 1,
                   updated_at = ?
               WHERE song_id = ?""",
            (_now(), song_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_transliteration(roman_name: str, language: str) -> str | None:
    """Return cached native-script name, or None if not yet transliterated."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT native_name FROM artist_transliterations WHERE roman_name = ? AND language = ?",
            (roman_name, language),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_transliteration(roman_name: str, language: str, native_name: str) -> None:
    """Insert or replace a transliteration cache entry."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO artist_transliterations
               (roman_name, language, native_name, created_at)
               VALUES (?, ?, ?, ?)""",
            (roman_name, language, native_name, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_run_summary(run_id: str) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()
