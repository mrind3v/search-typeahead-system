"""Search endpoint tests (Phase 5)."""

from __future__ import annotations

import asyncio
import time

import pytest

from src.cache.consistent_hash import ConsistentHashRing
from src.config import CACHE_KEY_PREFIX, REDIS_NODES
from src.database import get_suggestions_by_prefix


def test_search_returns_immediately(client) -> None:
    response = client.post("/search", json={"query": "iphone 15"})
    assert response.status_code == 200
    assert response.json() == {"message": "Searched"}


def test_search_strips_whitespace(client) -> None:
    response = client.post("/search", json={"query": "  iphone 15  "})
    assert response.status_code == 200
    assert response.json() == {"message": "Searched"}


def test_search_increments_count_after_flush(
    client, db_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.config.BATCH_FLUSH_INTERVAL_SECONDS", 0.05)

    for _ in range(5):
        response = client.post("/search", json={"query": "new query"})
        assert response.status_code == 200

    time.sleep(0.15)

    results = get_suggestions_by_prefix("new", db_path=db_path)
    assert results == [("new query", 5)]


def test_search_invalidates_cache_after_flush(
    client, fake_clients, db_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.config.BATCH_FLUSH_INTERVAL_SECONDS", 0.05)

    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"
    fake_clients[node].store[key] = '[["iphone 15", 500]]'

    client.post("/search", json={"query": "iphone 15"})
    time.sleep(0.15)

    response = client.get("/debug/cache", params={"q": prefix})
    assert response.status_code == 200
    assert response.json()["hit"] is False
    assert key not in fake_clients[node].store
