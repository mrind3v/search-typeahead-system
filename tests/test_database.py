"""SQLite database layer tests (Phase 1)."""

from pathlib import Path

import pytest

from src.database import (
    bulk_insert_queries,
    get_journal_mode,
    get_row_count,
    get_suggestions_by_prefix,
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


def test_bulk_insert_uses_total_changes_not_full_count_scan(db_path: Path) -> None:
    """bulk_insert_queries reports inserts via conn.total_changes."""
    inserted = bulk_insert_queries([("alpha", 1), ("beta", 2), ("gamma", 3)], db_path)
    assert inserted == 3
    assert get_row_count(db_path) == 3


def test_nocase_unique_constraint_prevents_case_duplicates(db_path: Path) -> None:
    assert bulk_insert_queries([("iPhone", 100)], db_path) == 1
    assert bulk_insert_queries([("iphone", 200)], db_path) == 0
    assert get_row_count(db_path) == 1


def test_get_suggestions_by_prefix_case_insensitive(db_path: Path) -> None:
    bulk_insert_queries([("iPhone 15", 500), ("android phone", 100)], db_path)
    results = get_suggestions_by_prefix("iph", db_path=db_path)
    assert results == [("iPhone 15", 500)]


def test_get_suggestions_by_prefix_escapes_percent_wildcard(db_path: Path) -> None:
    bulk_insert_queries(
        [
            ("100% cotton", 50),
            ("100x zoom", 10),
        ],
        db_path,
    )
    results = get_suggestions_by_prefix("100%", db_path=db_path)
    assert results == [("100% cotton", 50)]


def test_get_suggestions_by_prefix_escapes_underscore_wildcard(db_path: Path) -> None:
    bulk_insert_queries(
        [
            ("a_b test", 40),
            ("aab test", 5),
        ],
        db_path,
    )
    results = get_suggestions_by_prefix("a_b", db_path=db_path)
    assert results == [("a_b test", 40)]
