"""Daily decay scheduler for trending counts (Phase 6)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from src.cache.cache_manager import CacheManager
from src.config import DATABASE_PATH
from src.database import apply_decay

logger = logging.getLogger(__name__)


async def run_decay_scheduler(
    cache_manager_provider: Callable[[], CacheManager],
    db_path: str | Path | None = None,
    decay_factor: float | None = None,
    interval: float | None = None,
) -> None:
    """Periodically decay query counts and flush all suggestion cache entries."""
    from src import config

    resolved_db_path = db_path if db_path is not None else DATABASE_PATH

    def current_interval() -> float:
        return interval if interval is not None else config.DECAY_INTERVAL_SECONDS

    def current_factor() -> float:
        return decay_factor if decay_factor is not None else config.DECAY_FACTOR

    try:
        while True:
            await asyncio.sleep(current_interval())
            factor = current_factor()
            rows_updated = await asyncio.to_thread(
                apply_decay, factor, resolved_db_path
            )
            logger.info(
                "Decay applied (factor=%s): %s row(s) updated",
                factor,
                rows_updated,
            )
            cache_manager = cache_manager_provider()
            await cache_manager.flush_all_suggestion_cache()
    except asyncio.CancelledError:
        raise
