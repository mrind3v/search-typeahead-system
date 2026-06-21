# Typeahead System

Distributed typeahead search built with **FastAPI**, **Redis** (4-node consistent-hash cache), and **SQLite** (WAL). Implements prefix suggestions, batched search writes, nightly count decay, and in-process observability metrics.

## Quick Start

### Prerequisites

- **Docker and Docker Compose** — recommended; runs Redis, the FastAPI app, and the web UI with one command
- **Python 3.11+** — optional; only needed for local development without Docker

### Run with Docker (recommended)

From the project root:

```bash
docker compose up --build
```

This starts four Redis nodes plus the FastAPI app on [http://localhost:8000](http://localhost:8000).

On first run, if `data/queries.db` is missing inside the container, the app automatically seeds **200K synthetic queries** (may take a minute or two). The database is stored in a Docker volume (`app-data`) so later restarts reuse it.

Quick checks:

```bash
curl http://localhost:8000/health
# {"status":"OK"}

curl "http://localhost:8000/suggest?q=i"
# prefix suggestions (non-empty prefix required)

open http://localhost:8000
```

Stop the stack with `Ctrl+C`, or run detached with `docker compose up --build -d` and stop via `docker compose down`.

Optional environment variables for the `app` service (set in `docker-compose.yml` or override at runtime):

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEED_MIN_ROWS` | `200000` | Minimum rows when auto-seeding on first start |
| `DATABASE_PATH` | `/app/data/queries.db` | SQLite path inside the container |
| `REDIS_1_HOST` … `REDIS_4_HOST` | `redis-1` … `redis-4` | Redis service hostnames in Docker |

### Local development (optional)

**1. Start Redis (Docker)**

```bash
docker compose up -d redis-1 redis-2 redis-3 redis-4
```

**2. Install dependencies and seed data (host)**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed database (200K synthetic queries by default)
python scripts/load_data.py
```

**3. Run the API server (host)**

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) for the search UI (debounced suggestions, trending panel).

### Health & Metrics

```bash
curl http://localhost:8000/health
# {"status":"OK"}

curl http://localhost:8000/metrics
# latency p95, cache hit rate, DB read/write counters, batch write-reduction ratio
```

### Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Search UI |
| `GET` | `/health` | Liveness check |
| `GET` | `/suggest?q={prefix}` | Top-10 prefix suggestions (non-empty prefix) |
| `POST` | `/search` | Record a search event (batched write) |
| `GET` | `/trending` | Top trending queries by count |
| `GET` | `/cache/debug?prefix={prefix}` | Cache node, hit/miss, TTL |
| `GET` | `/metrics` | Latency, cache, DB, and batch metrics |

## Architecture Overview

```
Browser → FastAPI
           ├─ GET /suggest → Consistent Hash → Redis cache → SQLite fallback
           ├─ POST /search → asyncio.Queue → Batch Worker → SQLite + cache invalidation
           └─ Background: Decay Scheduler (daily 10% count decay + cache flush)
```

See [architecture.md](architecture.md) for design rationale (Trie rejection, consistent hashing, batch writes, nightly decay).

## Key Design Choices

| Decision | Rationale |
|----------|-----------|
| **SQLite + WAL** | Zero-config persistence; concurrent reads during batched writes |
| **Redis + consistent hashing** | Horizontally shard prefix cache across 4 nodes without a coordinator |
| **Non-empty prefix gate** | Skips suggest lookups for empty/whitespace-only input |
| **Per-prefix `asyncio.Lock`** | Thundering-herd protection on cold cache misses |
| **Lazy cache invalidation** | Batch worker deletes stale keys; rebuild on next suggest request |
| **`asyncio.Queue` batching** | Amortizes writes — 100 searches can collapse to 1 DB flush |
| **Scheduled decay (not write-time EMA)** | Nightly `count × 0.9` matches instructor “night script” pattern |
| **In-process metrics** | p95 latency, cache hit rate, DB counters, batch reduction ratio |

## Dataset

**[AmazonQAC](https://huggingface.co/datasets/amazon/AmazonQAC)** is recommended for production-scale data (~40M terms, `popularity` → `count`). The full download (~59GB) is impractical for local dev, so `scripts/load_data.py` generates **200K synthetic queries** by default (product categories, India-specific patterns, power-law counts).

```bash
python scripts/load_data.py
python scripts/load_data.py --csv data/queries.csv --min-rows 200000
```

`data/queries.db` is generated locally and is not committed.

## Project Structure

```
src/
├── main.py                 # FastAPI app, lifespan, middleware
├── config.py               # Redis nodes, batch/cache/decay settings
├── database.py             # SQLite layer
├── metrics.py              # Latency, DB, batch counters
├── middleware/latency.py   # p95 latency tracking
├── cache/
│   ├── consistent_hash.py
│   └── cache_manager.py
├── services/
│   ├── batch_worker.py
│   └── decay_scheduler.py
├── routers/
│   ├── suggest.py, search.py, trending.py
│   ├── debug.py, metrics.py
└── static/                 # Frontend UI
scripts/load_data.py
tests/
docs/screenshots/           # Optional demo screenshots
```

## Demo Screenshots

Optional UI captures live in [`docs/screenshots/`](docs/screenshots/) — for example, the search UI with suggestions, the trending panel, and JSON from `/metrics` or `/cache/debug?prefix=...`. With the server on port 8000:

```bash
open http://localhost:8000
curl http://localhost:8000/metrics | python -m json.tool
curl "http://localhost:8000/cache/debug?prefix=iph" | python -m json.tool
```

## Further Reading

- [architecture.md](architecture.md) — detailed flows and design decisions
- [context/implementation-plan.md](context/implementation-plan.md) — phased build plan
