"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.cache.cache_manager import CacheManager
from src.config import DATABASE_PATH
from src.database import init_db
from src.routers import debug, search, suggest, trending
from src.services.batch_worker import run_batch_worker
from src.services.decay_scheduler import run_decay_scheduler

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
    init_db(DATABASE_PATH)
    cache_manager = CacheManager()
    await cache_manager.connect()
    app.state.cache_manager = cache_manager

    search_queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    app.state.search_queue = search_queue
    track_background_task(
        asyncio.create_task(
            run_batch_worker(
                search_queue,
                lambda: app.state.cache_manager,
                db_path=DATABASE_PATH,
            )
        )
    )
    track_background_task(
        asyncio.create_task(
            run_decay_scheduler(
                lambda: app.state.cache_manager,
                db_path=DATABASE_PATH,
            )
        )
    )

    yield

    print("Typeahead system shutting down...")
    for task in list(background_tasks):
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    await cache_manager.close()
    print("Background tasks cancelled.")


app = FastAPI(title="Typeahead System", lifespan=lifespan)

app.include_router(suggest.router)
app.include_router(search.router)
app.include_router(debug.router)
app.include_router(trending.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "OK"}
