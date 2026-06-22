"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.cache.cache_manager import CacheManager
from src.config import REDIS_NODES
from src.database import bulk_insert_queries, init_db
from src.main import app


@pytest.fixture(autouse=True)
def _noop_cache_manager_lifecycle(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prevent TestClient lifespan from opening real Redis connections."""
    if request.node.fspath.basename in {
        "test_cache_manager.py",
        "test_decay_scheduler.py",
    }:
        return

    async def noop_connect(self: CacheManager) -> None:
        return None

    async def noop_close(self: CacheManager) -> None:
        return None

    async def noop_warm_all_from_db(self: CacheManager) -> None:
        return None

    monkeypatch.setattr(CacheManager, "connect", noop_connect)
    monkeypatch.setattr(CacheManager, "close", noop_close)
    monkeypatch.setattr(CacheManager, "warm_all_from_db", noop_warm_all_from_db)


class FakeRedis:
    """Minimal async Redis stand-in keyed by cache key string."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttl_values: dict[str, int] = {}
        self.get = AsyncMock(side_effect=self._get)
        self.set = AsyncMock(side_effect=self._set)
        self.delete = AsyncMock(side_effect=self._delete)
        self.ttl = AsyncMock(side_effect=self._ttl)
        self.scan = AsyncMock(side_effect=self._scan)

    async def _get(self, key: str) -> str | None:
        return self.store.get(key)

    async def _set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        if ex is not None:
            self.ttl_values[key] = ex
        return True

    async def _delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                self.ttl_values.pop(key, None)
                deleted += 1
        return deleted

    async def _ttl(self, key: str) -> int:
        if key not in self.store:
            return -2
        return self.ttl_values.get(key, -1)

    async def _scan(
        self, cursor: int = 0, match: str | None = None, count: int = 100
    ) -> tuple[int, list[str]]:
        keys = sorted(self.store.keys())
        if match and match.endswith("*"):
            prefix = match[:-1]
            keys = [key for key in keys if key.startswith(prefix)]
        return 0, keys


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "api_queries.db"
    init_db(path)
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
def cache_manager(fake_clients: dict[str, FakeRedis], db_path: Path) -> CacheManager:
    return CacheManager(
        clients={name: client for name, client in fake_clients.items()},
        db_path=db_path,
    )


@pytest.fixture
def client(
    cache_manager: CacheManager, db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    from src.database import get_all_queries

    monkeypatch.setattr("src.config.DATABASE_PATH", str(db_path))
    monkeypatch.setattr("src.main.DATABASE_PATH", str(db_path))

    async def warm_test_cache() -> None:
        queries = await asyncio.to_thread(get_all_queries, db_path)
        await cache_manager.warm_prefixes_for_queries(queries)

    asyncio.run(warm_test_cache())
    with TestClient(app) as test_client:
        app.state.cache_manager = cache_manager
        yield test_client
