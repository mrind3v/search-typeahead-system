"""POST /search endpoint (Phase 5)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str


@router.post("/search")
async def search(request: Request, body: SearchRequest) -> dict[str, str]:
    """Accept a search event and return immediately; counts are batched asynchronously."""
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    queue: asyncio.Queue[tuple[str, int]] = request.app.state.search_queue
    await queue.put((query, 1))
    return {"message": "Searched"}
