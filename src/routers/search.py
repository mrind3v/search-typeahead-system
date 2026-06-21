"""POST /search endpoint (Phase 5)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str


@router.post("/search")
async def search(request: Request, body: SearchRequest) -> dict[str, str]:
    """Accept a search event and return immediately; counts are batched asynchronously."""
    queue: asyncio.Queue[tuple[str, int]] = request.app.state.search_queue
    await queue.put((body.query.strip(), 1))
    return {"message": "Searched"}
