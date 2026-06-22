"""Suggest endpoint tests (Phase 4)."""

from __future__ import annotations

import asyncio

from src.cache.consistent_hash import ConsistentHashRing
from src.config import CACHE_KEY_PREFIX, MIN_PREFIX_LENGTH, REDIS_NODES
from src.database import get_suggestions_by_prefix


def test_get_suggestions_by_prefix_returns_empty_for_empty_prefix(db_path) -> None:
    assert get_suggestions_by_prefix("", db_path=db_path) == []


def test_get_suggestions_by_prefix_returns_results_for_one_char_prefix(db_path) -> None:
    results = get_suggestions_by_prefix("i", db_path=db_path)
    assert results == [
        ("iphone 15", 500),
        ("iphone 14", 400),
    ]


def test_get_suggestions_by_prefix_returns_results_for_two_char_prefix(db_path) -> None:
    results = get_suggestions_by_prefix("ip", db_path=db_path)
    assert results == [
        ("iphone 15", 500),
        ("iphone 14", 400),
    ]


def test_suggest_returns_empty_for_empty_prefix(client) -> None:
    response = client.get("/suggest", params={"q": ""})
    assert response.status_code == 200
    assert response.json() == {"suggestions": []}


def test_suggest_returns_empty_for_whitespace_only_prefix(client) -> None:
    response = client.get("/suggest", params={"q": "   "})
    assert response.status_code == 200
    assert response.json() == {"suggestions": []}


def test_suggest_returns_results_for_one_char_prefix(client) -> None:
    response = client.get("/suggest", params={"q": "i"})
    assert response.status_code == 200
    assert response.json() == {
        "suggestions": [
            {"query": "iphone 15", "count": 500},
            {"query": "iphone 14", "count": 400},
        ]
    }


def test_suggest_returns_results_for_two_char_prefix(client) -> None:
    response = client.get("/suggest", params={"q": "ip"})
    assert response.status_code == 200
    assert response.json() == {
        "suggestions": [
            {"query": "iphone 15", "count": 500},
            {"query": "iphone 14", "count": 400},
        ]
    }


def test_suggest_returns_empty_on_cache_miss_without_db(client, cache_manager, fake_clients) -> None:
    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"

    # Client fixture warms cache; clear the prefix under test to simulate a miss.
    fake_clients[node].store.pop(key, None)

    db_calls = 0

    def db_loader(prefix_arg: str, limit: int, db_path) -> list[tuple[str, int]]:
        nonlocal db_calls
        db_calls += 1
        return [("iphone 15", 500), ("iphone 14", 400)]

    cache_manager._db_loader = db_loader

    response = client.get("/suggest", params={"q": prefix})
    assert response.status_code == 200
    assert response.json() == {"suggestions": []}
    assert db_calls == 0
    assert key not in fake_clients[node].store


def test_suggest_returns_cached_results_without_db(client, cache_manager, fake_clients) -> None:
    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"
    fake_clients[node].store[key] = '[["cached query", 999]]'

    db_calls = 0

    def db_loader(prefix_arg: str, limit: int, db_path) -> list[tuple[str, int]]:
        nonlocal db_calls
        db_calls += 1
        return []

    cache_manager._db_loader = db_loader

    response = client.get("/suggest", params={"q": prefix})
    assert response.status_code == 200
    assert response.json() == {
        "suggestions": [{"query": "cached query", "count": 999}]
    }
    assert db_calls == 0


def test_suggest_lstrip_preserves_trailing_whitespace(client) -> None:
    response = client.get("/suggest", params={"q": "  iph  "})
    assert response.status_code == 200
    assert response.json() == {"suggestions": []}


def test_suggest_lstrip_leading_whitespace(client) -> None:
    response = client.get("/suggest", params={"q": "  iph"})
    assert response.status_code == 200
    assert len(response.json()["suggestions"]) == 2


def test_suggest_respects_min_prefix_length_constant(client) -> None:
    short_prefix = "a" * (MIN_PREFIX_LENGTH - 1)
    response = client.get("/suggest", params={"q": short_prefix})
    assert response.json() == {"suggestions": []}


def test_cache_manager_inspect_does_not_fill_cache(cache_manager, fake_clients) -> None:
    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"

    result = asyncio.run(cache_manager.inspect_cache(prefix))

    assert result["hit"] is False
    assert key not in fake_clients[node].store
