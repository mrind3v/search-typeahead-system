# Architecture

## System Diagram

```mermaid
flowchart TB
    subgraph Client["Browser"]
        SI["Search Input + Debounce"]
        SD["Suggestions Dropdown"]
        TP["Trending Panel"]
    end

    subgraph FastAPI["FastAPI (lifespan)"]
        MW["Latency Middleware"]
        SR["GET /suggest"]
        SER["POST /search"]
        TR["GET /trending"]
        DR["GET /cache/debug"]
        MR["GET /metrics"]

        Q["asyncio.Queue"]
        BW["Batch Worker"]
        DS["Decay Scheduler"]
        WARM["Cache warm / re-warm"]

        CH["Consistent Hash Ring"]
        DB["SQLite + WAL"]
    end

    subgraph Redis["Independent Redis nodes (consistent hash)"]
        R1["redis-1 :6379"]
        R2["redis-2 :6380"]
        R3["redis-3 :6381"]
        R4["redis-4 :6382"]
    end

    SI --> MW
    TP --> MW
    MW --> SR
    MW --> SER
    MW --> TR
    MW --> DR

    SR -->|"cache-only read"| CH
    DR -->|"inspect routing + key"| CH
    CH --> Redis

    TR -->|"direct read"| DB

    SER --> Q --> BW --> DB
    BW -->|"re-warm updated prefixes"| WARM
    WARM -->|"read"| DB
    WARM --> CH

    DB -->|"startup warm_all_from_db"| WARM

    DS -->|"apply_decay"| DB
    DS -->|"flush + full re-warm"| WARM

    MR --> DB
```

## Why Not a Trie?

A **prefix trie** (or compressed trie / DAFSA) is the classic in-memory structure for autocomplete: O(prefix length) lookup, natural top-K by stored counts at nodes.

We **rejected a trie** for this implementation because:

1. **Persistence and scale** — Our source of truth is SQLite with 200K+ rows. Keeping a full trie in memory duplicates the dataset and complicates recovery after restarts.
2. **Distributed cache** — The course design shards **per-prefix keys** across Redis nodes via consistent hashing. A trie would live on one process; replicating or partitioning a mutable trie across nodes adds coordination overhead that prefix-key caching avoids.
3. **Write amplification** — Each search updates counts. With a trie, many nodes along the path may need updates. Batched SQLite `UPSERT` + Redis re-warming is simpler and matches the taught flow.
4. **MVP fit** — `LIKE 'prefix%'` with a collation index on `query` is sufficient at demo scale. The lecture recommends a 3-character prefix gate in production to bound scan cost; this implementation uses `MIN_PREFIX_LENGTH = 1` for demo/dev responsiveness.

**Trade-off:** We avoid a hot in-memory trie by serving reads from a pre-warmed Redis cache. SQLite holds query/count data and feeds cache warming at startup, after batch flushes, and after decay — not request-time fallback for `/suggest`.

## Consistent Hashing

Four independent Redis instances act as a **distributed cache**, not Redis Cluster. A **consistent hash ring** (MD5, 150 virtual nodes per physical node) maps each prefix string to exactly one node.

**Why consistent hashing?**

| Benefit | Explanation |
|---------|-------------|
| Stable routing | Same prefix always maps to the same node → high hit rate |
| Minimal remapping | Adding/removing a node only moves ~1/N of keys |
| No single hot spot | Virtual nodes spread prefixes evenly across machines |
| Simple client logic | Application picks the node; no central proxy required |

**Flow:** `get_node("iph")` → `redis-2` → `GET suggest:iph`. Invalidation deletes `suggest:i`, `suggest:ip`, `suggest:iph`, … on their respective nodes.

## Prefix Gate

Suggestions return `[]` when the trimmed prefix is empty (`MIN_PREFIX_LENGTH = 1` in `src/config.py`):

- `src/database.py` — skips SQL for prefixes shorter than `MIN_PREFIX_LENGTH` during cache warming
- `GET /suggest` — enforces gate before Redis lookup (cache miss also returns `[]`; no SQLite read)
- `src/static/app.js` — mirrors `MIN_PREFIX_LENGTH = 1`; no API call until the user has typed at least one character

The lecture used **3 characters** as a product choice to limit how many rows a short prefix can match (e.g. `"a"` → huge scan). This repo keeps **`MIN_PREFIX_LENGTH = 1`** so the demo UI responds on the first keystroke; warming still issues one bounded `LIKE` query per prefix key, not per suggest request.

## Request Flows

### Suggest (`GET /suggest?q=iph`)

1. Reject if `len(q.lstrip()) < MIN_PREFIX_LENGTH` (empty after trim)
2. `consistent_hash.get_node(prefix)` → Redis node
3. Cache hit → return JSON suggestions
4. Cache miss → return `[]` (no SQLite read on the request path)

SQLite is **not** queried during suggest. The cache is populated separately (see below).

### Trending (`GET /trending`)

1. Read top queries directly from SQLite (`get_trending_queries`)
2. Return JSON `trending` list — no Redis, no consistent hash

The browser trending panel polls this endpoint on an interval; it is independent of the suggestion cache.

### Cache debug (`GET /cache/debug?prefix=…`)

1. Resolve routing via consistent hash (`get_node_for_prefix`)
2. Inspect the `suggest:{prefix}` key on the selected Redis node (hit/miss, TTL)
3. Does **not** load from SQLite or fill the cache on miss

### Cache warming (SQLite → Redis)

| Trigger | Action |
|---------|--------|
| **App startup** | `init_db` → `warm_all_from_db()` — load all queries from SQLite, warm every prefix ≥ `MIN_PREFIX_LENGTH` into Redis via consistent hash |
| **Batch flush** | `increment_counts` in SQLite, then `warm_prefixes_for_queries()` — **overwrite** affected prefix keys in Redis (not a request-time fallback) |
| **Decay cycle** | `apply_decay` in SQLite, then `flush_all_suggestion_cache()` and `warm_all_from_db()` — full cache rebuild from decayed counts |

Warming reads SQLite via `get_suggestions_by_prefix` and stores results in Redis with TTL 300s. Request-time `/suggest` never triggers warming.

### Search (`POST /search`)

1. Validate non-empty query; return `{"message": "Searched"}` immediately
2. Push `(query, 1)` onto global `asyncio.Queue`; increment search-event metric
3. Batch worker aggregates into `{query: accumulated_count}`
4. Flush when buffer ≥ 100 queries **or** 10s timer elapses
5. `increment_counts` (single DB write per flush) + `warm_prefixes_for_queries()` to re-warm/overwrite affected prefix keys in Redis

**Write reduction:** 50 identical searches → 1 buffer entry → 1 DB flush. Metrics expose `write_reduction_ratio = search_events / db_writes`. Cache re-warm runs after the DB write, not on `/suggest` cache miss.

### Nightly Decay

Every 24 hours the decay scheduler runs:

```sql
UPDATE queries SET count = CAST(count * 0.9 AS INTEGER) WHERE count > 0;
```

Then `flush_all_suggestion_cache()` deletes all `suggest:*` keys across every Redis node and `warm_all_from_db()` rebuilds the cache from SQLite so rankings reflect decayed counts. This is a **scheduled night script**, not per-write exponential moving average — simpler and aligned with the lecture.

## SQLite Schema

```sql
PRAGMA journal_mode=WAL;

CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT UNIQUE NOT NULL COLLATE NOCASE,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queries_prefix ON queries(query COLLATE NOCASE);
```

`COLLATE NOCASE` prevents case-sensitive duplicate queries. LIKE patterns escape `%` and `_` for literal prefix matching.

## Observability (`GET /metrics`)

| Metric | Source |
|--------|--------|
| `latency_ms.p95` | Rolling window (1000 samples) from HTTP middleware |
| `cache.hit_rate` | `hits / (hits + misses)` from `CacheManager` |
| `database.reads` / `writes` | Counters in `database.py` |
| `batch.search_events` | Incremented on each `POST /search` |
| `batch.write_reduction_ratio` | `search_events / db_writes` |

## Background Tasks (Lifespan)

| Task | Role |
|------|------|
| Startup (`lifespan`) | `init_db`, connect Redis nodes, `warm_all_from_db()` (SQLite → cache) |
| Batch worker | Consume search queue, flush to SQLite, re-warm affected prefixes |
| Decay scheduler | Daily count decay in SQLite, then full cache flush + re-warm |

On shutdown: cancel tasks, flush remaining batch buffer, close Redis clients.

## Dataset Strategy

See [README.md](README.md#dataset). Default dev workflow uses 200K synthetic queries; AmazonQAC is recommended when exporting real autocomplete training data.
