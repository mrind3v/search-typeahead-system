"""GET /metrics endpoint (Phase 7)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.cache.cache_manager import CacheManager
from src.metrics import get_metrics_snapshot

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics(request: Request) -> dict[str, object]:
    """Return latency, cache, database, and batch write-reduction metrics."""
    cache_manager: CacheManager = request.app.state.cache_manager
    return get_metrics_snapshot(
        cache_hits=cache_manager.cache_hits,
        cache_misses=cache_manager.cache_misses,
    )
