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


def get_run_summary(run_id: str) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()
