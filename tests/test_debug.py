"""Debug cache endpoint tests (Phase 4)."""

from __future__ import annotations

import asyncio

from src.cache.consistent_hash import ConsistentHashRing
from src.config import CACHE_KEY_PREFIX, REDIS_NODES


def test_debug_cache_reports_miss_without_filling_cache(
    client, cache_manager, fake_clients
) -> None:
    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"

    response = client.get("/debug/cache", params={"q": prefix})

    assert response.status_code == 200
    payload = response.json()
    assert payload["prefix"] == prefix
    assert payload["node"] == node
    assert payload["cache_key"] == key
    assert payload["hit"] is False
    assert payload["ttl_remaining"] is None
    assert key not in fake_clients[node].store


def test_debug_cache_reports_hit_and_ttl(client, fake_clients) -> None:
    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"
    fake_clients[node].store[key] = '[["iphone 15", 500]]'
    fake_clients[node].ttl_values[key] = 240

    response = client.get("/debug/cache", params={"q": prefix})

    assert response.status_code == 200
    payload = response.json()
    assert payload["hit"] is True
    assert payload["node"] == node
    assert payload["ttl_remaining"] == 240


def test_debug_cache_strips_whitespace(client) -> None:
    response = client.get("/debug/cache", params={"q": "  iph  "})
    assert response.status_code == 200
    assert response.json()["prefix"] == "iph"


def test_inspect_cache_read_only(cache_manager, fake_clients) -> None:
    prefix = "and"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"

    db_calls = 0

    def db_loader(prefix_arg: str, limit: int, db_path) -> list[tuple[str, int]]:
        nonlocal db_calls
        db_calls += 1
        return [("android phone", 100)]

    cache_manager._db_loader = db_loader

    result = asyncio.run(cache_manager.inspect_cache(prefix))

    assert result["hit"] is False
    assert db_calls == 0
    assert key not in fake_clients[node].store
