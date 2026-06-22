"""Metrics endpoint and instrumentation tests (Phase 7)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from src.metrics import (
    get_metrics_snapshot,
    record_batch_flush,
    record_db_read,
    record_db_write,
    record_latency,
    record_search_event,
    reset_metrics,
)


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    reset_metrics()
    yield
    reset_metrics()


def test_percentile_and_snapshot_helpers() -> None:
    for value in (10.0, 20.0, 30.0, 40.0, 100.0):
        record_latency(value / 1000.0)
    record_db_read(2)
    record_db_write(1)
    record_search_event(5)
    record_batch_flush(1)

    snapshot = get_metrics_snapshot(cache_hits=3, cache_misses=1)

    assert snapshot["latency_ms"]["samples"] == 5
    assert snapshot["latency_ms"]["p95"] == 100.0
    assert snapshot["cache"]["hits"] == 3
    assert snapshot["cache"]["misses"] == 1
    assert snapshot["cache"]["hit_rate"] == 0.75
    assert snapshot["database"]["reads"] == 2
    assert snapshot["database"]["writes"] == 1
    assert snapshot["batch"]["search_events"] == 5
    assert snapshot["batch"]["flushes"] == 1
    assert snapshot["batch"]["queries_written"] == 1
    assert snapshot["batch"]["write_reduction_ratio"] == 5.0


def test_metrics_endpoint_returns_defaults(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()

    assert "latency_ms" in payload
    assert "cache" in payload
    assert "database" in payload
    assert "batch" in payload
    assert payload["cache"]["hit_rate"] is None
    assert payload["batch"]["search_events"] == 0


def test_metrics_reflect_cache_hits_and_db_reads(client: TestClient) -> None:
    reads_before = client.get("/metrics").json()["database"]["reads"]

    client.get("/suggest", params={"q": "iph"})
    client.get("/suggest", params={"q": "iph"})

    response = client.get("/metrics")
    payload = response.json()

    assert payload["cache"]["hits"] == 2
    assert payload["cache"]["misses"] == 0
    assert payload["cache"]["hit_rate"] == 1.0
    assert payload["database"]["reads"] == reads_before


def test_metrics_reflect_search_events_and_batch_reduction(client: TestClient) -> None:
    import time

    for index in range(100):
        client.post("/search", json={"query": f"metric query {index}"})

    time.sleep(0.15)

    response = client.get("/metrics")
    payload = response.json()

    assert payload["batch"]["search_events"] == 100
    assert payload["database"]["writes"] >= 1
    assert payload["batch"]["write_reduction_ratio"] == pytest.approx(
        100 / payload["database"]["writes"]
    )
