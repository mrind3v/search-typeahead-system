#!/bin/sh
set -e

DB_PATH="${DATABASE_PATH:-/app/data/queries.db}"
SEED_MIN_ROWS="${SEED_MIN_ROWS:-200000}"

mkdir -p "$(dirname "$DB_PATH")"

if [ ! -f "$DB_PATH" ]; then
  echo "Database not found at ${DB_PATH}; seeding with ${SEED_MIN_ROWS} rows..."
  python scripts/load_data.py --db "$DB_PATH" --min-rows "$SEED_MIN_ROWS"
else
  echo "Using existing database at ${DB_PATH}"
fi

exec uvicorn src.main:app --host 0.0.0.0 --port 8000
