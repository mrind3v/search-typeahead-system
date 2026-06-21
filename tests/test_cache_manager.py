"""Redis cache manager tests (Phase 3)."""

from __future__ import annotations

import asyncio
import gc
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
        self.delete = AsyncMock(side_effect=self._delete)

    async def _get(self, key: str) -> str | None:
        return self.store.get(key)

    async def _set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        return True

    async def _delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted


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


def test_concurrent_same_prefix_serializes_db_load(
    cache_manager: CacheManager,
) -> None:
    import threading

    prefix = "iph"
    db_calls = 0
    release_event = threading.Event()

    def slow_db_loader(
        prefix_arg: str,
        limit: int,
        db_path: Path | None,
    ) -> list[tuple[str, int]]:
        nonlocal db_calls
        db_calls += 1
        release_event.wait(timeout=1.0)
        return [("iphone 15", 500)]

    cache_manager._db_loader = slow_db_loader

    async def run_concurrent_requests() -> list[list[tuple[str, int]]]:
        tasks = [asyncio.create_task(cache_manager.get_suggestions(prefix)) for _ in range(5)]
        await asyncio.sleep(0.05)
        assert db_calls == 1
        release_event.set()
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_concurrent_requests())

    assert all(result == [("iphone 15", 500)] for result in results)
    assert db_calls == 1
    assert cache_manager.cache_misses == 1
    assert cache_manager.cache_hits == 4


def test_invalidate_prefixes_deletes_all_query_prefix_keys(
    cache_manager: CacheManager,
    fake_clients: dict[str, FakeRedis],
) -> None:
    query = "abc"
    ring = ConsistentHashRing(NODE_NAMES)

    for length in range(1, len(query) + 1):
        prefix = query[:length]
        node = ring.get_node(prefix)
        key = f"{CACHE_KEY_PREFIX}{prefix}"
        fake_clients[node].store[key] = "[]"

    asyncio.run(cache_manager.invalidate_prefixes(query))

    for length in range(1, len(query) + 1):
        prefix = query[:length]
        node = ring.get_node(prefix)
        key = f"{CACHE_KEY_PREFIX}{prefix}"
        assert key not in fake_clients[node].store

    nodes_with_keys = {ring.get_node(query[:length]) for length in range(1, len(query) + 1)}
    for node_name in nodes_with_keys:
        fake_clients[node_name].delete.assert_awaited()


def test_prefix_lock_weakref_cleanup_allows_recreation(
    cache_manager: CacheManager,
) -> None:
    prefix = "weakref-test"
    lock = cache_manager._get_lock(prefix)
    assert cache_manager._prefix_locks[prefix] is lock

    del lock
    gc.collect()

    assert prefix not in cache_manager._prefix_locks
    new_lock = cache_manager._get_lock(prefix)
    assert isinstance(new_lock, asyncio.Lock)


def test_connect_ping_failure_logs_warning_and_does_not_raise(
    caplog: pytest.LogCaptureFixture,
) -> None:
    manager = CacheManager()
    mock_client = MagicMock()
    mock_client.ping = AsyncMock(side_effect=ConnectionError("refused"))

    async def run_connect() -> None:
        with patch("src.cache.cache_manager.aioredis.Redis", return_value=mock_client):
            with caplog.at_level(logging.WARNING, logger="src.cache.cache_manager"):
                await manager.connect()

    asyncio.run(run_connect())

    assert mock_client.ping.await_count == len(REDIS_NODES)
    assert len(manager._clients) == len(REDIS_NODES)
    assert any("Redis ping failed" in record.message for record in caplog.records)


def test_invalidate_prefixes_partial_failure_logs_and_deletes_healthy_nodes(
    cache_manager: CacheManager,
    fake_clients: dict[str, FakeRedis],
    caplog: pytest.LogCaptureFixture,
) -> None:
    query = "xyz"
    ring = ConsistentHashRing(NODE_NAMES)
    failing_node: str | None = None

    for length in range(1, len(query) + 1):
        prefix = query[:length]
        node = ring.get_node(prefix)
        key = f"{CACHE_KEY_PREFIX}{prefix}"
        fake_clients[node].store[key] = "[]"
        if failing_node is None:
            failing_node = node

    assert failing_node is not None
    fake_clients[failing_node].delete = AsyncMock(
        side_effect=RuntimeError("node unavailable"),
    )

    async def run_invalidate() -> None:
        with caplog.at_level(logging.WARNING, logger="src.cache.cache_manager"):
            await cache_manager.invalidate_prefixes(query)

    asyncio.run(run_invalidate())

    for length in range(1, len(query) + 1):
        prefix = query[:length]
        node = ring.get_node(prefix)
        key = f"{CACHE_KEY_PREFIX}{prefix}"
        if node == failing_node:
            assert key in fake_clients[node].store
        else:
            assert key not in fake_clients[node].store

    assert any("Cache invalidation failed" in record.message for record in caplog.records)

