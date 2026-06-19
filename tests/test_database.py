"""SQLite database layer tests (Phase 1)."""

from pathlib import Path

import pytest

from src.database import (
    bulk_insert_queries,
    get_journal_mode,
    get_row_count,
    init_db,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_queries.db"


def test_init_db_creates_schema(db_path: Path) -> None:
    init_db(db_path)
    assert get_row_count(db_path) == 0
    assert get_journal_mode(db_path) == "wal"


def test_journal_mode_is_wal(db_path: Path) -> None:
    init_db(db_path)
    assert get_journal_mode(db_path) == "wal"


def test_bulk_insert_increases_row_count(db_path: Path) -> None:
    rows = [
        ("iphone", 100_000),
        ("iphone 15", 85_000),
        ("java tutorial", 40_000),
    ]
    inserted = bulk_insert_queries(rows, db_path)
    assert inserted == 3
    assert get_row_count(db_path) == 3


def test_bulk_insert_ignores_duplicate_queries(db_path: Path) -> None:
    bulk_insert_queries([("iphone", 100)], db_path)
    inserted = bulk_insert_queries([("iphone", 200)], db_path)
    assert inserted == 0
    assert get_row_count(db_path) == 1


def test_bulk_insert_empty_returns_zero(db_path: Path) -> None:
    assert bulk_insert_queries([], db_path) == 0
