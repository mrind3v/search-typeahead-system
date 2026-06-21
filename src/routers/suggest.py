"""GET /suggest endpoint (Phase 4)."""

from fastapi import APIRouter, Query

from src.config import MIN_PREFIX_LENGTH, SUGGESTION_LIMIT
from src.database import get_suggestions_by_prefix

router = APIRouter(tags=["suggest"])


def is_valid_prefix(prefix: str) -> bool:
    """Return True when the prefix meets the minimum length gate."""
    return len(prefix.strip()) >= MIN_PREFIX_LENGTH


@router.get("/suggest")
async def suggest(q: str = Query(default="")) -> list[dict[str, str | int]]:
    """Return top suggestions for a query prefix (DB-only until cache layer)."""
    prefix = q.strip()
    if not is_valid_prefix(prefix):
        return []

    results = get_suggestions_by_prefix(prefix, limit=SUGGESTION_LIMIT)
    return [{"query": query, "count": count} for query, count in results]
