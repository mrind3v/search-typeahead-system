"""Suggestion prefix gate and API tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import MIN_PREFIX_LENGTH
from src.database import bulk_insert_queries, get_suggestions_by_prefix, init_db
from src.main import app
from src.routers.suggest import is_valid_prefix

client = TestClient(app)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "suggestions.db"
    init_db(path)
    bulk_insert_queries(
        [
            ("iphone", 100_000),
            ("iphone 15", 85_000),
            ("ipad pro", 40_000),
            ("java tutorial", 25_000),
        ],
        path,
    )
    return path


def test_min_prefix_length_constant() -> None:
    assert MIN_PREFIX_LENGTH == 3


def test_is_valid_prefix_helper() -> None:
    assert is_valid_prefix("iph") is True
    assert is_valid_prefix("  iph  ") is True
    assert is_valid_prefix("ip") is False
    assert is_valid_prefix("") is False
    assert is_valid_prefix("  ") is False


def test_get_suggestions_returns_empty_for_short_prefix(db_path: Path) -> None:
    assert get_suggestions_by_prefix("ip", db_path=db_path) == []
    assert get_suggestions_by_prefix("  i ", db_path=db_path) == []


def test_get_suggestions_returns_matches_for_valid_prefix(db_path: Path) -> None:
    results = get_suggestions_by_prefix("iph", db_path=db_path)
    queries = [query for query, _ in results]
    assert "iphone" in queries
    assert "iphone 15" in queries
    assert all(len(query) >= MIN_PREFIX_LENGTH for query in queries)


def test_get_suggestions_ordered_by_count_desc(db_path: Path) -> None:
    results = get_suggestions_by_prefix("iph", db_path=db_path)
    counts = [count for _, count in results]
    assert counts == sorted(counts, reverse=True)


def test_suggest_endpoint_returns_empty_for_short_prefix() -> None:
    response = client.get("/suggest", params={"q": "ip"})
    assert response.status_code == 200
    assert response.json() == []


def test_suggest_endpoint_returns_matches(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setattr(
        "src.routers.suggest.get_suggestions_by_prefix",
        lambda prefix, limit=10: get_suggestions_by_prefix(prefix, limit, db_path),
    )
    response = client.get("/suggest", params={"q": "iph"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert all("query" in item and "count" in item for item in data)
