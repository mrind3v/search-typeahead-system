"""GET /suggest endpoint (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.cache.cache_manager import CacheManager
from src.config import MIN_PREFIX_LENGTH

router = APIRouter(tags=["suggest"])


def _get_cache_manager(request: Request) -> CacheManager:
    return request.app.state.cache_manager


@router.get("/suggest")
async def suggest(request: Request, q: str = "") -> dict[str, list[dict[str, int | str]]]:
    """Return prefix suggestions from cache with SQLite fallback."""
    prefix = q.lstrip()
    if len(prefix) < MIN_PREFIX_LENGTH:
        return {"suggestions": []}

    cache_manager = _get_cache_manager(request)
    results = await cache_manager.get_suggestions(prefix)
    return {
        "suggestions": [
            {"query": query, "count": count} for query, count in results
        ]
    }
