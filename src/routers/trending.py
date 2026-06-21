"""GET /trending endpoint (Phase 6)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from src.config import TRENDING_LIMIT
from src.database import get_trending_queries

router = APIRouter(tags=["trending"])


@router.get("/trending")
async def trending(
    limit: int = Query(default=TRENDING_LIMIT, ge=1, le=50),
) -> dict[str, list[dict[str, int | str]]]:
    """Return top global trending queries ordered by count."""
    from src import config

    results = await asyncio.to_thread(
        get_trending_queries, limit, config.DATABASE_PATH
    )
    return {
        "trending": [
            {"query": query, "count": count} for query, count in results
        ]
    }
