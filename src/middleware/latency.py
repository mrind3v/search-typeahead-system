"""Request latency middleware for p95 tracking (Phase 7)."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.metrics import record_latency


class LatencyMiddleware(BaseHTTPMiddleware):
    """Record per-request latency for p95 computation."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        record_latency(time.perf_counter() - start)
        return response
