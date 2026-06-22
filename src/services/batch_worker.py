"""Batch worker for aggregated search writes (Phase 5)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path

from src.cache.cache_manager import CacheManager
from src.config import DATABASE_PATH
from src.database import increment_counts
from src.metrics import record_batch_flush


async def run_batch_worker(
    queue: asyncio.Queue[tuple[str, int]],
    cache_manager_provider: Callable[[], CacheManager],
    db_path: str | Path | None = None,
    batch_size: int | None = None,
    flush_interval: float | None = None,
) -> None:
    """Consume search events, aggregate counts, and flush on timer or size threshold."""
    from src import config

    buffer: dict[str, int] = {}
    last_flush_at = time.monotonic()
    resolved_db_path = db_path if db_path is not None else DATABASE_PATH

    def current_batch_size() -> int:
        return batch_size if batch_size is not None else config.BATCH_SIZE

    def current_flush_interval() -> float:
        return (
            flush_interval
            if flush_interval is not None
            else config.BATCH_FLUSH_INTERVAL_SECONDS
        )

    async def flush_buffer() -> None:
        nonlocal buffer, last_flush_at
        if not buffer:
            return

        updates = list(buffer.items())
        buffer = {}
        last_flush_at = time.monotonic()

        record_batch_flush(len(updates))
        await asyncio.to_thread(increment_counts, updates, resolved_db_path)
        cache_manager = cache_manager_provider()
        await cache_manager.warm_prefixes_for_queries([q for q, _ in updates])

    try:
        while True:
            elapsed = time.monotonic() - last_flush_at
            timeout = max(0.0, current_flush_interval() - elapsed)
            try:
                query, count = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                await flush_buffer()
                continue

            buffer[query] = buffer.get(query, 0) + count
            queue.task_done()

            if len(buffer) >= current_batch_size():
                await flush_buffer()
    except asyncio.CancelledError:
        while True:
            try:
                query, count = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            buffer[query] = buffer.get(query, 0) + count
            queue.task_done()

        await flush_buffer()
        raise
