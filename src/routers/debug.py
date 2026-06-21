"""GET /debug/cache endpoint (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.cache.cache_manager import CacheManager
from src.config import CACHE_KEY_PREFIX, MIN_PREFIX_LENGTH

router = APIRouter(prefix="/debug", tags=["debug"])


def _get_cache_manager(request: Request) -> CacheManager:
    return request.app.state.cache_manager


@router.get("/cache")
async def debug_cache(request: Request, q: str = "") -> dict[str, str | bool | int | None]:
    """Inspect which Redis node owns a prefix and whether the cache key is set."""
    prefix = q.strip()
    cache_manager = _get_cache_manager(request)
    if len(prefix) < MIN_PREFIX_LENGTH:
        return {
            "prefix": prefix,
            "node": cache_manager.get_node_for_prefix(prefix),
            "cache_key": f"{CACHE_KEY_PREFIX}{prefix}",
            "hit": False,
            "ttl_remaining": None,
        }
    return await cache_manager.inspect_cache(prefix)
