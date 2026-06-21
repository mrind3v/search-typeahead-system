"""SQLite database layer (Phase 1)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path

from src.config import DATABASE_PATH, MIN_PREFIX_LENGTH

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT UNIQUE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queries_prefix ON queries(query COLLATE NOCASE);
"""


def _resolve_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return Path(DATABASE_PATH)
    return Path(db_path)


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with WAL journal mode enabled."""
    path = _resolve_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    """Create the queries table and prefix index if they do not exist."""
    with get_connection(db_path) as conn:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()


def bulk_insert_queries(
    rows: Iterable[tuple[str, int]],
    db_path: str | Path | None = None,
) -> int:
    """Bulk insert (query, count) pairs. Returns number of new rows inserted."""
    data = list(rows)
    if not data:
        return 0

    init_db(db_path)
    with get_connection(db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        conn.executemany(
            "INSERT OR IGNORE INTO queries (query, count) VALUES (?, ?)",
            data,
        )
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        return after - before


def get_row_count(db_path: str | Path | None = None) -> int:
    """Return total number of rows in the queries table."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM queries").fetchone()
        return int(row[0])


def get_journal_mode(db_path: str | Path | None = None) -> str:
    """Return the active SQLite journal mode (expected: wal)."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("PRAGMA journal_mode;").fetchone()
        return str(row[0]).lower()


def get_suggestions_by_prefix(
    prefix: str,
    limit: int = 10,
    db_path: str | Path | None = None,
) -> list[tuple[str, int]]:
    """Return prefix-matching queries ordered by count descending (Phase 4)."""
    stripped = prefix.strip()
    if len(stripped) < MIN_PREFIX_LENGTH:
        return []

    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT query, count
            FROM queries
            WHERE query LIKE ? ESCAPE '\\'
            ORDER BY count DESC
            LIMIT ?
            """,
            (f"{stripped}%", limit),
        ).fetchall()
        return [(str(row["query"]), int(row["count"])) for row in rows]


def increment_counts(
    updates: Sequence[tuple[str, int]],
    db_path: str | Path | None = None,
) -> None:
    """Upsert query counts by adding deltas (Phase 5 batch worker)."""
    if not updates:
        return

    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO queries (query, count) VALUES (?, ?)
            ON CONFLICT(query) DO UPDATE SET count = count + excluded.count
            """,
            updates,
        )
        conn.commit()


def apply_decay(
    factor: float = 0.9,
    db_path: str | Path | None = None,
) -> int:
    """Apply multiplicative decay to all positive counts (Phase 6)."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE queries SET count = CAST(count * ? AS INTEGER) WHERE count > 0",
            (factor,),
        )
        conn.commit()
        return cursor.rowcount
