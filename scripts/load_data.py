#!/usr/bin/env python3
"""Load query dataset into SQLite (Phase 1)."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATABASE_PATH
from src.database import bulk_insert_queries, get_row_count, init_db

DEFAULT_CSV = ROOT / "data" / "queries.csv"
MIN_QUERY_COUNT = 100_000
BATCH_SIZE = 5_000

PRODUCTS = (
    "iphone",
    "samsung galaxy",
    "macbook",
    "ipad",
    "airpods",
    "laptop",
    "wireless earbuds",
    "gaming monitor",
    "mechanical keyboard",
    "python tutorial",
    "java tutorial",
    "react hooks",
    "docker compose",
    "kubernetes pods",
    "aws lambda",
    "machine learning",
    "data science",
    "neural network",
    "typescript generics",
    "graphql api",
)

MODIFIERS = (
    "pro",
    "max",
    "ultra",
    "plus",
    "mini",
    "2024",
    "2025",
    "review",
    "price",
    "deals",
    "best",
    "cheap",
    "near me",
    "for beginners",
    "crash course",
    "charger",
    "case",
    "screen protector",
    "warranty",
    "unboxing",
)

QUALIFIERS = (
    "buy",
    "how to",
    "what is",
    "vs",
    "compare",
    "fix",
    "install",
    "setup",
    "config",
    "example",
)


def read_csv_rows(csv_path: Path) -> list[tuple[str, int]]:
    """Read query,count rows from a CSV file."""
    if not csv_path.is_file():
        return []

    rows: list[tuple[str, int]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return rows

        for record in reader:
            query = (record.get("query") or "").strip()
            if not query:
                continue
            try:
                count = int(record.get("count") or 0)
            except ValueError:
                continue
            rows.append((query, count))
    return rows


def generate_synthetic_queries(target_count: int, seed: int = 42) -> list[tuple[str, int]]:
    """Generate realistic unique search queries with frequency counts."""
    rng = random.Random(seed)
    queries: dict[str, int] = {}
    attempt = 0

    while len(queries) < target_count:
        attempt += 1
        pattern = attempt % 5
        if pattern == 0:
            query = f"{rng.choice(QUALIFIERS)} {rng.choice(PRODUCTS)}"
        elif pattern == 1:
            query = f"{rng.choice(PRODUCTS)} {rng.choice(MODIFIERS)}"
        elif pattern == 2:
            query = f"{rng.choice(PRODUCTS)} {rng.choice(MODIFIERS)} {rng.randint(1, 99)}"
        elif pattern == 3:
            query = f"{rng.choice(PRODUCTS)} {rng.choice(MODIFIERS)} variant {rng.randint(1, 5000)}"
        else:
            query = (
                f"{rng.choice(QUALIFIERS)} {rng.choice(PRODUCTS)} "
                f"{rng.choice(MODIFIERS)} {rng.randint(1, 9999)}"
            )

        query = " ".join(query.split())
        if query not in queries:
            queries[query] = rng.randint(1, 100_000)

    return list(queries.items())


def load_rows(
    csv_path: Path,
    min_rows: int = MIN_QUERY_COUNT,
    seed: int = 42,
) -> list[tuple[str, int]]:
    """Combine CSV data with synthetic queries until min_rows is reached."""
    rows = read_csv_rows(csv_path)
    existing = {query for query, _ in rows}

    if len(rows) < min_rows:
        needed = min_rows - len(rows)
        synthetic = generate_synthetic_queries(needed, seed=seed)
        for query, count in synthetic:
            if query not in existing:
                rows.append((query, count))
                existing.add(query)

    return rows


def load_in_batches(rows: list[tuple[str, int]], db_path: Path) -> int:
    """Insert rows in batches for efficient bulk loading."""
    total_inserted = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        total_inserted += bulk_insert_queries(batch, db_path)
    return total_inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load search queries into SQLite.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV file with query,count columns (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(DATABASE_PATH),
        help=f"SQLite database path (default: {DATABASE_PATH})",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=MIN_QUERY_COUNT,
        help=f"Minimum queries to load (default: {MIN_QUERY_COUNT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for synthetic query generation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db.resolve()
    csv_path = args.csv.resolve()

    rows = load_rows(csv_path, min_rows=args.min_rows, seed=args.seed)
    if len(rows) < args.min_rows:
        raise SystemExit(
            f"Expected at least {args.min_rows} queries, prepared {len(rows)}"
        )

    init_db(db_path)
    inserted = load_in_batches(rows, db_path)
    total = get_row_count(db_path)

    print(f"Prepared {len(rows)} queries from {csv_path.name}")
    print(f"Inserted {inserted} new rows into {db_path}")
    print(f"Total rows in database: {total}")


if __name__ == "__main__":
    main()
