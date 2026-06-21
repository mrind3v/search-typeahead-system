# End-to-End Testing Guide

This guide walks through running the typeahead system as a full stack on your machine: four Redis nodes in Docker, SQLite on disk, and the FastAPI application on the host. Use it for manual verification, demos, and submission checklists.

> **Important:** `docker-compose.yml` starts **Redis only**. The FastAPI server always runs on the host via `uvicorn` (port 8000).

## Contents

- [Prerequisites](#prerequisites)
- [One-Time Setup](#one-time-setup)
- [Start Redis (Docker)](#start-redis-docker)
- [Seed the Database](#seed-the-database)
- [Start the API Server](#start-the-api-server)
- [Smoke Test: Health and UI](#smoke-test-health-and-ui)
- [API Walkthrough (curl)](#api-walkthrough-curl)
- [Full E2E Flow: Cache, Batch, and Metrics](#full-e2e-flow-cache-batch-and-metrics)
- [Batch Worker Verification](#batch-worker-verification)
- [Decay Scheduler](#decay-scheduler)
- [Automated Test Suite](#automated-test-suite)
- [Teardown and Cleanup](#teardown-and-cleanup)
- [Quick Reference](#quick-reference)
- [Submission and Demo Checklist](#submission-and-demo-checklist)

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.11+** | Virtual environment recommended |
| **Docker & Docker Compose** | For the four Redis nodes only |
| **curl** | API smoke tests |
| **Git** | Clone the repository |

From the repository root:

```bash
cd /path/to/typeahead-system
```

---

## One-Time Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Keep this shell active for all subsequent commands in this guide.

---

## Start Redis (Docker)

Start four Redis nodes mapped to host ports **6379–6382**:

```bash
docker-compose up -d
```

| Container | Host port | Internal port |
|-----------|-----------|---------------|
| `typeahead-redis-1` | 6379 | 6379 |
| `typeahead-redis-2` | 6380 | 6379 |
| `typeahead-redis-3` | 6381 | 6379 |
| `typeahead-redis-4` | 6382 | 6379 |

### Health checks

Confirm all containers are running and healthy:

```bash
docker-compose ps
```

Each service should show `healthy`. You can also ping each node directly:

```bash
redis-cli -p 6379 ping   # PONG
redis-cli -p 6380 ping
redis-cli -p 6381 ping
redis-cli -p 6382 ping
```

If `redis-cli` is not installed on the host, use Docker:

```bash
docker exec typeahead-redis-1 redis-cli ping
```

### Common fixes

| Problem | Fix |
|---------|-----|
| **Port already in use** | Stop the conflicting process or change host port mappings in `docker-compose.yml`. |
| **Container unhealthy** | `docker-compose logs redis-1` (or the failing node). Wait a few seconds and retry `docker-compose ps`. |
| **Stale data from a previous run** | `docker-compose down -v` removes volumes and resets Redis state. |
| **API cannot connect to Redis** | Ensure containers are up and `src/config.py` points to `localhost:6379–6382`. |

---

## Seed the Database

Load search queries into SQLite (`data/queries.db`). The loader merges any rows from `data/queries.csv` with synthetic queries until the minimum row count is reached.

### Full dataset (default — ~500K rows)

```bash
python scripts/load_data.py
```

Expect output similar to:

```text
Prepared 500000 queries from queries.csv
Inserted 500000 new rows into .../data/queries.db
Total rows in database: 500000
```

This may take a minute or two depending on disk speed.

### Quick dataset (smoke testing — 10K rows)

```bash
python scripts/load_data.py --min-rows 10000
```

Use the quick load for faster iteration when you only need to verify API behavior, not query volume.

### Re-seed from scratch

Delete the existing database and run the loader again:

```bash
rm -f data/queries.db
python scripts/load_data.py --min-rows 10000   # or omit for full 500K
```

`data/queries.db` is generated locally and is not committed to the repository.

---

## Start the API Server

With Redis running and the database seeded, start FastAPI on the host:

```bash
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

On startup you should see:

```text
Typeahead system starting up...
```

The server listens at [http://localhost:8000](http://localhost:8000). Background tasks start automatically:

- **Batch worker** — aggregates `POST /search` events and flushes to SQLite
- **Decay scheduler** — applies nightly count decay (24-hour interval)

---

## Smoke Test: Health and UI

### Health endpoint

```bash
curl -s http://localhost:8000/health
```

Expected response:

```json
{"status":"OK"}
```

### UI checklist

Open [http://localhost:8000](http://localhost:8000) and verify:

| Check | Expected behavior |
|-------|-------------------|
| **3-character minimum** | Typing fewer than 3 characters shows no suggestions |
| **Debounced suggestions** | Suggestions appear after ~300 ms pause while typing |
| **Suggestion list** | Up to 10 results with query text and count |
| **Keyboard navigation** | Arrow keys move selection; Enter selects |
| **Search button** | Submits the current query via `POST /search` |
| **Trending panel** | Top queries load on page open; refreshes every 60 s |
| **Status messages** | Hint and status areas update without errors |

Try prefixes that exist in the seeded data, for example `iph`, `lap`, `jee`, or `dio` (Diwali).

---

## API Walkthrough (curl)

All examples assume the server is running on port 8000.

### `GET /health`

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

### `GET /suggest?q={prefix}`

Prefix must be at least 3 characters. Leading whitespace is stripped via `lstrip()`; trailing whitespace is preserved.

```bash
curl -s "http://localhost:8000/suggest?q=iph" | python -m json.tool
```

Example response:

```json
{
  "suggestions": [
    {"query": "iphone 15 pro", "count": 12345},
    {"query": "iphone 14", "count": 8900}
  ]
}
```

Short prefix (returns empty list):

```bash
curl -s "http://localhost:8000/suggest?q=ip" | python -m json.tool
# {"suggestions": []}
```

### `POST /search`

Records a search event. The response is immediate; counts are written asynchronously by the batch worker.

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "iphone 15 pro"}' | python -m json.tool
```

Expected:

```json
{"message": "Searched"}
```

### `GET /trending`

```bash
curl -s http://localhost:8000/trending | python -m json.tool
```

Optional `limit` query parameter (1–50, default 10):

```bash
curl -s "http://localhost:8000/trending?limit=5" | python -m json.tool
```

### `GET /cache/debug?prefix={prefix}`

Inspects which Redis node owns a prefix and whether the cache key is set. **Does not** fill the cache from the database — it is read-only inspection.

```bash
curl -s "http://localhost:8000/cache/debug?prefix=iph" | python -m json.tool
```

Example miss (before any suggest request warms the cache):

```json
{
  "prefix": "iph",
  "node": "redis-2",
  "cache_key": "suggest:iph",
  "hit": false,
  "ttl_remaining": null
}
```

**Whitespace behavior:** The `prefix` parameter uses `lstrip()`, so leading spaces are removed but trailing spaces are kept. For example, `prefix=%20%20iph%20%20` resolves to `"iph  "`.

Prefixes shorter than 3 characters still return routing metadata with `hit: false`:

```bash
curl -s "http://localhost:8000/cache/debug?prefix=ip" | python -m json.tool
```

### `GET /metrics`

```bash
curl -s http://localhost:8000/metrics | python -m json.tool
```

Example structure:

```json
{
  "latency_ms": {"p95": 12.5, "samples": 42},
  "cache": {"hits": 10, "misses": 3, "hit_rate": 0.769},
  "database": {"reads": 3, "writes": 1},
  "batch": {
    "search_events": 150,
    "flushes": 2,
    "queries_written": 5,
    "write_reduction_ratio": 30.0
  }
}
```

---

## Full E2E Flow: Cache, Batch, and Metrics

This sequence exercises cache warming, batch writes, cache invalidation, and metrics in one pass.

### Step 1 — Cold cache miss

```bash
curl -s "http://localhost:8000/cache/debug?prefix=lap" | python -m json.tool
```

Confirm `"hit": false`.

### Step 2 — Warm the cache

```bash
curl -s "http://localhost:8000/suggest?q=lap" | python -m json.tool
```

First request is a cache miss (SQLite read). Subsequent requests for the same prefix should hit Redis.

### Step 3 — Confirm cache hit

```bash
curl -s "http://localhost:8000/cache/debug?prefix=lap" | python -m json.tool
```

Confirm `"hit": true` and a positive `ttl_remaining` (default TTL is 300 seconds).

### Step 4 — Record search events

Send several searches for the same query to exercise batch aggregation:

```bash
for i in $(seq 1 20); do
  curl -s -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{"query": "laptop pro 2025"}' > /dev/null
done
echo "done"
```

### Step 5 — Wait for batch flush

The batch worker flushes when the buffer reaches **100 unique queries** or after **10 seconds** of inactivity. Wait at least 10 seconds, then check metrics:

```bash
sleep 12
curl -s http://localhost:8000/metrics | python -m json.tool
```

Look for increased `batch.flushes`, `batch.queries_written`, and `database.writes`. The `write_reduction_ratio` (search events ÷ DB writes) should be greater than 1 when multiple events were aggregated.

### Step 6 — Cache invalidation after flush

After a flush, affected prefix cache keys are deleted. Re-check debug:

```bash
curl -s "http://localhost:8000/cache/debug?prefix=lap" | python -m json.tool
```

If the flushed query shared prefixes with cached keys, you may see `hit: false` until the next suggest request repopulates the cache.

### Step 7 — Trending reflects new counts

```bash
curl -s http://localhost:8000/trending | python -m json.tool
```

Repeated searches should eventually increase counts for matching queries (after batch flush).

---

## Batch Worker Verification

The batch worker (`src/services/batch_worker.py`) runs inside the API process. Default settings from `src/config.py`:

| Setting | Value |
|---------|-------|
| `BATCH_SIZE` | 100 unique queries |
| `BATCH_FLUSH_INTERVAL_SECONDS` | 10 seconds |

### Timer-based flush

Send a single search event, then wait 10+ seconds without sending more:

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "timer flush test"}'

sleep 12
curl -s http://localhost:8000/metrics | python -m json.tool
```

`batch.flushes` should increment and `database.writes` should increase.

### Size-based flush

Send 100 **distinct** queries rapidly to trigger a size-threshold flush before the 10-second timer:

```bash
for i in $(seq 1 100); do
  curl -s -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"size flush query $i\"}" > /dev/null
done

curl -s http://localhost:8000/metrics | python -m json.tool
```

`batch.flushes` should increment immediately (or within a second) without waiting for the timer.

### Aggregation check

Send 50 identical search events, wait for flush, then suggest:

```bash
for i in $(seq 1 50); do
  curl -s -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{"query": "aggregation test query"}' > /dev/null
done

sleep 12
curl -s "http://localhost:8000/suggest?q=agg" | python -m json.tool
```

The count for `aggregation test query` should reflect all 50 events combined into one database write.

---

## Decay Scheduler

The decay scheduler (`src/services/decay_scheduler.py`) runs as a background task with these defaults:

| Setting | Value |
|---------|-------|
| `DECAY_INTERVAL_SECONDS` | 86,400 (24 hours) |
| `DECAY_FACTOR` | 0.9 (multiply all counts by 90%) |

On each cycle it:

1. Applies `count × 0.9` to every row in SQLite
2. Flushes all `suggest:*` keys from every Redis node

### Waiting 24 hours is impractical for manual E2E

For automated verification, use pytest with a shortened interval:

```bash
pytest tests/test_decay_scheduler.py -v
```

Tests run the scheduler with `interval=0.2` seconds and confirm counts decay (e.g., 1000 → 900) and cache is flushed.

### Optional SQLite spot-check

If you want to observe decay logic without waiting a day, query the database directly before and after a test run:

```bash
sqlite3 data/queries.db "SELECT query, count FROM queries ORDER BY count DESC LIMIT 5;"
```

Run `pytest tests/test_decay_scheduler.py -v` against a temporary database (tests use `tmp_path`, not your production `data/queries.db`). To spot-check decay on your live database you would need to temporarily lower `DECAY_INTERVAL_SECONDS` in `src/config.py` — only do this in a throwaway environment, not for submission demos.

---

## Automated Test Suite

### Run all tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### pytest (FakeRedis) vs full-stack E2E

| Aspect | `pytest tests/` | Manual E2E (this guide) |
|--------|-----------------|-------------------------|
| **Redis** | In-memory `FakeRedis` per node | Real Redis in Docker |
| **SQLite** | Temporary `tmp_path` databases | `data/queries.db` on disk |
| **Network** | `TestClient` in-process | HTTP to `localhost:8000` |
| **Batch/decay timing** | Shortened intervals in tests | Production config (10 s / 24 h) |
| **Purpose** | Regression coverage, CI | Integration validation, demos |

`tests/conftest.py` patches `CacheManager.connect` and `close` so pytest never opens real Redis connections. Tests in `tests/test_cache_manager.py` use the real `CacheManager` class with `FakeRedis` clients.

### Targeted test runs

```bash
pytest tests/test_suggestions.py -v    # suggest endpoint
pytest tests/test_search.py -v         # search endpoint
pytest tests/test_batch_worker.py -v   # batch aggregation and flush
pytest tests/test_decay_scheduler.py -v
pytest tests/test_debug.py -v          # /cache/debug including lstrip behavior
pytest tests/test_metrics.py -v
```

---

## Teardown and Cleanup

### Stop the API server

Press `Ctrl+C` in the terminal running uvicorn. You should see:

```text
Typeahead system shutting down...
Background tasks cancelled.
```

### Stop Redis

```bash
docker-compose down
```

Remove Redis data volumes as well:

```bash
docker-compose down -v
```

### Remove generated database (optional)

```bash
rm -f data/queries.db
```

### Deactivate virtual environment

```bash
deactivate
```

---

## Quick Reference

| Step | Command |
|------|---------|
| Activate venv | `source .venv/bin/activate` |
| Start Redis | `docker-compose up -d` |
| Check Redis health | `docker-compose ps` |
| Seed DB (full) | `python scripts/load_data.py` |
| Seed DB (quick) | `python scripts/load_data.py --min-rows 10000` |
| Start API | `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload` |
| Health check | `curl http://localhost:8000/health` |
| Suggestions | `curl "http://localhost:8000/suggest?q=iph"` |
| Search event | `curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"query":"test"}'` |
| Trending | `curl http://localhost:8000/trending` |
| Cache debug | `curl "http://localhost:8000/cache/debug?prefix=iph"` |
| Metrics | `curl http://localhost:8000/metrics` |
| Run tests | `pytest tests/ -v` |
| Stop Redis | `docker-compose down` |
| UI | [http://localhost:8000](http://localhost:8000) |

---

## Submission and Demo Checklist

Use this list when recording a demo or preparing a submission.

- [ ] `docker-compose up -d` — four Redis nodes healthy on ports 6379–6382
- [ ] `python scripts/load_data.py` (or `--min-rows 10000` for a faster demo)
- [ ] `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload` — API on host, not in Docker
- [ ] `curl http://localhost:8000/health` returns `{"status":"OK"}`
- [ ] UI at `http://localhost:8000` — type 3+ characters, see debounced suggestions
- [ ] Trending panel loads top queries
- [ ] `GET /suggest?q=...` returns ranked suggestions
- [ ] `POST /search` returns `{"message":"Searched"}`
- [ ] `GET /cache/debug?prefix=...` shows node routing; `hit` flips to `true` after suggest warms cache
- [ ] `GET /metrics` shows latency p95, cache hit rate, and batch write-reduction ratio
- [ ] Batch flush observable after 10 s or 100 distinct queries
- [ ] `pytest tests/ -v` passes
- [ ] Screenshots saved to `docs/screenshots/` (search UI, trending, metrics JSON)
- [ ] `docker-compose down` when finished

---

## See Also

- [README.md](../README.md) — project overview and quick start
- [architecture.md](../architecture.md) — design rationale and data flows
