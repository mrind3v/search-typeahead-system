"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.routers import suggest

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
    # Future phases: start batch worker and decay scheduler via track_background_task()

    yield

    print("Typeahead system shutting down...")
    for task in list(background_tasks):
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    print("Background tasks cancelled.")


app = FastAPI(title="Typeahead System", lifespan=lifespan)
app.include_router(suggest.router)
app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("src/static/index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "OK"}
