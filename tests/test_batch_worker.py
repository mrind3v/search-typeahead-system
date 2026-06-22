"""Batch worker tests (Phase 5)."""

from __future__ import annotations

import asyncio

import pytest

from src.cache.cache_manager import CacheManager
from src.database import bulk_insert_queries, get_suggestions_by_prefix, init_db
from src.services.batch_worker import run_batch_worker


@pytest.fixture
def worker_db_path(tmp_path):
    path = tmp_path / "worker_queries.db"
    init_db(path)
    bulk_insert_queries([("iphone 15", 100)], path)
    return path


@pytest.fixture
def worker_cache_manager(fake_clients, worker_db_path) -> CacheManager:
    return CacheManager(
        clients={name: client for name, client in fake_clients.items()},
        db_path=worker_db_path,
    )


async def _run_worker_until_flush(
    queue: asyncio.Queue[tuple[str, int]],
    cache_manager: CacheManager,
    db_path,
    *,
    batch_size: int = 100,
    flush_interval: float = 0.05,
    stop_after: float = 0.2,
) -> None:
    task = asyncio.create_task(
        run_batch_worker(
            queue,
            lambda: cache_manager,
            db_path=db_path,
            batch_size=batch_size,
            flush_interval=flush_interval,
        )
    )
    await asyncio.sleep(stop_after)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_batch_worker_aggregates_same_query(
    worker_cache_manager, worker_db_path, fake_clients
) -> None:
    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    for _ in range(50):
        queue.put_nowait(("iphone 15", 1))

    asyncio.run(
        _run_worker_until_flush(queue, worker_cache_manager, worker_db_path)
    )

    results = get_suggestions_by_prefix("iph", db_path=worker_db_path)
    assert results == [("iphone 15", 150)]


def test_batch_worker_flushes_on_size_threshold(
    worker_cache_manager, worker_db_path
) -> None:
    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    for index in range(100):
        queue.put_nowait((f"query {index}", 1))

    asyncio.run(
        _run_worker_until_flush(
            queue,
            worker_cache_manager,
            worker_db_path,
            batch_size=100,
            flush_interval=60.0,
            stop_after=0.1,
        )
    )

    assert get_suggestions_by_prefix("query", db_path=worker_db_path)


def test_batch_worker_rebuilds_prefixes_on_flush(
    worker_cache_manager, worker_db_path, fake_clients
) -> None:
    from src.cache.consistent_hash import ConsistentHashRing
    from src.config import CACHE_KEY_PREFIX, REDIS_NODES

    prefix = "iph"
    node = ConsistentHashRing([node.name for node in REDIS_NODES]).get_node(prefix)
    key = f"{CACHE_KEY_PREFIX}{prefix}"
    fake_clients[node].store[key] = '[["iphone 15", 100]]'

    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    queue.put_nowait(("iphone 15", 1))

    asyncio.run(
        _run_worker_until_flush(queue, worker_cache_manager, worker_db_path)
    )

    assert key in fake_clients[node].store
    assert fake_clients[node].store[key] == '[["iphone 15", 150]]'


def test_batch_worker_shutdown_flushes_remaining_buffer(
    worker_cache_manager, worker_db_path
) -> None:
    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    queue.put_nowait(("shutdown query", 3))

    async def run_and_cancel() -> None:
        task = asyncio.create_task(
            run_batch_worker(
                queue,
                lambda: worker_cache_manager,
                db_path=worker_db_path,
                batch_size=100,
                flush_interval=60.0,
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_and_cancel())

    results = get_suggestions_by_prefix("shut", db_path=worker_db_path)
    assert results == [("shutdown query", 3)]
