"""Redis cache manager tests (Phase 3)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.cache.cache_manager import CacheManager
from src.cache.consistent_hash import ConsistentHashRing
from src.config import CACHE_KEY_PREFIX, CACHE_TTL_SECONDS, REDIS_NODES, SUGGESTION_LIMIT
from src.database import bulk_insert_queries

NODE_NAMES = [node.name for node in REDIS_NODES]


class FakeRedis:
    """Minimal async Redis stand-in keyed by cache key string."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.get = AsyncMock(side_effect=self._get)
        self.set = AsyncMock(side_effect=self._set)

    async def _get(self, key: str) -> str | None:
        return self.store.get(key)

    async def _set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        return True


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "cache_queries.db"
    bulk_insert_queries(
        [
            ("iphone 15", 500),
            ("iphone 14", 400),
            ("android phone", 100),
        ],
        path,
    )
    return path


@pytest.fixture
def fake_clients() -> dict[str, FakeRedis]:
    return {node.name: FakeRedis() for node in REDIS_NODES}


@pytest.fixture
def cache_manager(
    fake_clients: dict[str, FakeRedis],
    db_path: Path,
) -> CacheManager:
    return CacheManager(
        clients={name: client for name, client in fake_clients.items()},
        db_path=db_path,
    )


def _expected_node(prefix: str) -> str:
    return ConsistentHashRing(NODE_NAMES).get_node(prefix)


def test_cache_hit_returns_cached_data_without_db(
    cache_manager: CacheManager,
    fake_clients: dict[str, FakeRedis],
) -> None:
    prefix = "iph"
    node = _expected_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"
    fake_clients[node].store[key] = '[["iphone 15", 500], ["iphone 14", 400]]'

    db_calls = 0

    def db_loader(prefix_arg: str, limit: int, db_path: Path | None) -> list[tuple[str, int]]:
        nonlocal db_calls
        db_calls += 1
        return []

    cache_manager._db_loader = db_loader

    result = asyncio.run(cache_manager.get_suggestions(prefix))

    assert result == [("iphone 15", 500), ("iphone 14", 400)]
    assert cache_manager.cache_hits == 1
    assert cache_manager.cache_misses == 0
    assert db_calls == 0


def test_cache_miss_fills_from_db_and_sets_ttl(
    cache_manager: CacheManager,
    fake_clients: dict[str, FakeRedis],
) -> None:
    prefix = "iph"
    node = _expected_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"

    result = asyncio.run(cache_manager.get_suggestions(prefix))

    assert result == [("iphone 15", 500), ("iphone 14", 400)]
    assert cache_manager.cache_hits == 0
    assert cache_manager.cache_misses == 1
    assert key in fake_clients[node].store
    fake_clients[node].set.assert_awaited_once_with(
        key,
        '[["iphone 15", 500], ["iphone 14", 400]]',
        ex=CACHE_TTL_SECONDS,
    )


def test_set_suggestions_uses_configured_limit_from_db(
    cache_manager: CacheManager,
    fake_clients: dict[str, FakeRedis],
    db_path: Path,
) -> None:
    rows = [(f"iphone {index}", index) for index in range(20, 0, -1)]
    bulk_insert_queries(rows, db_path)

    result = asyncio.run(cache_manager.get_suggestions("iphone"))

    assert len(result) == SUGGESTION_LIMIT
    assert result[0][1] >= result[-1][1]
