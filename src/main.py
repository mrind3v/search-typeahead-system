"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.cache.cache_manager import CacheManager
from src.routers import debug, search, suggest

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Tracked background tasks started during lifespan (batch worker, decay scheduler, etc.)
background_tasks: set[asyncio.Task[object]] = set()


def track_background_task(task: asyncio.Task[object]) -> asyncio.Task[object]:
    """Register a background task for cancellation on shutdown."""
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global background_tasks
    background_tasks = set()

    print("Typeahead system starting up...")
    cache_manager = CacheManager()
    await cache_manager.connect()
    app.state.cache_manager = cache_manager

    search_queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    app.state.search_queue = search_queue

    yield

    print("Typeahead system shutting down...")
    await cache_manager.close()
    for task in list(background_tasks):
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    print("Background tasks cancelled.")


app = FastAPI(title="Typeahead System", lifespan=lifespan)

app.include_router(suggest.router)
app.include_router(search.router)
app.include_router(debug.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "OK"}
