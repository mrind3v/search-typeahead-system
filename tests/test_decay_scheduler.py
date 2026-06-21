"""Decay scheduler tests (Phase 6)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.cache.cache_manager import CacheManager
from src.database import bulk_insert_queries, get_trending_queries, init_db
from src.services.decay_scheduler import run_decay_scheduler


@pytest.fixture
def decay_db_path(tmp_path):
    path = tmp_path / "decay_queries.db"
    init_db(path)
    bulk_insert_queries(
        [
            ("hot query", 1000),
            ("warm query", 500),
            ("cold query", 10),
        ],
        path,
    )
    return path


@pytest.fixture
def decay_cache_manager(fake_clients, decay_db_path) -> CacheManager:
    return CacheManager(
        clients={name: client for name, client in fake_clients.items()},
        db_path=decay_db_path,
    )


async def _run_scheduler_one_cycle(
    cache_manager: CacheManager,
    db_path,
    *,
    interval: float = 0.2,
    decay_factor: float = 0.9,
) -> None:
    task = asyncio.create_task(
        run_decay_scheduler(
            lambda: cache_manager,
            db_path=db_path,
            decay_factor=decay_factor,
            interval=interval,
        )
    )
    await asyncio.sleep(interval + 0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_decay_scheduler_applies_decay_to_database(
    decay_cache_manager, decay_db_path
) -> None:
    asyncio.run(_run_scheduler_one_cycle(decay_cache_manager, decay_db_path))

    trending = get_trending_queries(db_path=decay_db_path)
    assert trending == [
        ("hot query", 900),
        ("warm query", 450),
        ("cold query", 9),
    ]


def test_decay_scheduler_flushes_all_cache(
    decay_cache_manager, decay_db_path, fake_clients
) -> None:
    from src.config import CACHE_KEY_PREFIX, REDIS_NODES

    for node in REDIS_NODES:
        fake_clients[node.name].store[f"{CACHE_KEY_PREFIX}iph"] = "[]"
        fake_clients[node.name].store[f"{CACHE_KEY_PREFIX}and"] = "[]"

    flush_mock = AsyncMock()
    with patch.object(
        decay_cache_manager, "flush_all_suggestion_cache", flush_mock
    ):
        asyncio.run(_run_scheduler_one_cycle(decay_cache_manager, decay_db_path))

    flush_mock.assert_awaited_once()


def test_decay_scheduler_cancellation_exits_cleanly(
    decay_cache_manager, decay_db_path
) -> None:
    async def run_and_cancel() -> None:
        task = asyncio.create_task(
            run_decay_scheduler(
                lambda: decay_cache_manager,
                db_path=decay_db_path,
                interval=60.0,
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_and_cancel())
