# Typeahead System

Distributed typeahead search with FastAPI, Redis caching, and SQLite.

## Phase 0: Bootstrap

### Prerequisites

- Python 3.11+
- Docker and Docker Compose

### Setup

```bash
# Start Redis nodes (ports 6379-6382)
docker-compose up -d

# Install dependencies (use virtual environment)
python3.11 -m venv .venv  # or python3.12 / python3.13 (3.11+ required)
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the API server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"OK"}
```

## Phase 1: Data Layer

Load at least **500,000** search queries into SQLite (WAL mode). The loader reads
`data/queries.csv` when present (optional seed from AmazonQAC export or custom data)
and generates additional realistic synthetic queries to reach the minimum dataset size.

### Dataset recommendation

**[AmazonQAC](https://huggingface.co/datasets/amazon/AmazonQAC)** is the recommended
open-source dataset (~40M terms, `popularity` → `count`, CDLA-Permissive-2.0). The
full download (~59GB) is not used by default. Instead, the loader synthesizes 500K
diverse queries including India-specific patterns (cricket, festivals, exams, entertainment).

```bash
source .venv/bin/activate
python scripts/load_data.py
```

Optional flags:

```bash
python scripts/load_data.py --csv data/queries.csv --db data/queries.db --min-rows 500000
```

Verify the seeded database:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/queries.db')
print('count:', conn.execute('SELECT COUNT(*) FROM queries').fetchone()[0])
print('journal_mode:', conn.execute('PRAGMA journal_mode').fetchone()[0])
"
```

`data/queries.db` is generated locally and is not committed to git.

### Project Structure

```
src/
├── main.py              # FastAPI app with lifespan
├── config.py            # Redis nodes, batch settings
├── database.py          # SQLite layer (Phase 1)
├── cache/               # Consistent hashing + cache manager
├── services/            # Batch worker, decay scheduler
├── routers/             # suggest, search, debug endpoints
└── static/              # Frontend UI
scripts/
└── load_data.py         # Dataset loader
data/
└── queries.csv          # Query dataset
```

## Architecture

See [architecture.md](architecture.md) and [implementation-plan.md](implementation-plan.md).
