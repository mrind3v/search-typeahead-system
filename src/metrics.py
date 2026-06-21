"""In-process metrics for latency, cache, database, and batch writes (Phase 7)."""

from __future__ import annotations

import math
import threading
from collections import deque

_LATENCY_WINDOW_SIZE = 1000

_lock = threading.Lock()
_latencies_ms: deque[float] = deque(maxlen=_LATENCY_WINDOW_SIZE)
_db_reads = 0
_db_writes = 0
_search_events = 0
_batch_flushes = 0
_batch_queries_written = 0


def record_latency(seconds: float) -> None:
    """Record request latency in milliseconds."""
    with _lock:
        _latencies_ms.append(seconds * 1000.0)


def record_db_read(count: int = 1) -> None:
    with _lock:
        global _db_reads
        _db_reads += count


def record_db_write(count: int = 1) -> None:
    with _lock:
        global _db_writes
        _db_writes += count


def record_search_event(count: int = 1) -> None:
    with _lock:
        global _search_events
        _search_events += count


def record_batch_flush(queries_written: int) -> None:
    with _lock:
        global _batch_flushes, _batch_queries_written
        _batch_flushes += 1
        _batch_queries_written += queries_written


def reset_metrics() -> None:
    """Clear all in-process counters (used in tests)."""
    with _lock:
        global _db_reads, _db_writes, _search_events, _batch_flushes, _batch_queries_written
        _latencies_ms.clear()
        _db_reads = 0
        _db_writes = 0
        _search_events = 0
        _batch_flushes = 0
        _batch_queries_written = 0


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(math.ceil(percentile * len(ordered)) - 1, len(ordered) - 1))
    return ordered[index]


def _cache_hit_rate(cache_hits: int, cache_misses: int) -> float | None:
    total = cache_hits + cache_misses
    if total == 0:
        return None
    return cache_hits / total


def _batch_write_reduction_ratio(search_events: int, db_writes: int) -> float | None:
    if db_writes == 0:
        return None
    return search_events / db_writes


def get_metrics_snapshot(cache_hits: int = 0, cache_misses: int = 0) -> dict[str, object]:
    """Return a JSON-serializable metrics snapshot."""
    with _lock:
        latencies = list(_latencies_ms)
        db_reads = _db_reads
        db_writes = _db_writes
        search_events = _search_events
        batch_flushes = _batch_flushes
        batch_queries_written = _batch_queries_written

    return {
        "latency_ms": {
            "p95": _percentile(latencies, 0.95),
            "samples": len(latencies),
        },
        "cache": {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_rate": _cache_hit_rate(cache_hits, cache_misses),
        },
        "database": {
            "reads": db_reads,
            "writes": db_writes,
        },
        "batch": {
            "search_events": search_events,
            "flushes": batch_flushes,
            "queries_written": batch_queries_written,
            "write_reduction_ratio": _batch_write_reduction_ratio(
                search_events, db_writes
            ),
        },
    }
