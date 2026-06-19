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
