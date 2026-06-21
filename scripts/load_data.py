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
MIN_QUERY_COUNT = 500_000
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

CATEGORY_PRODUCTS: dict[str, tuple[str, ...]] = {
    "Electronics": (
        "smart tv",
        "bluetooth speaker",
        "power bank",
        "dslr camera",
        "smartwatch",
        "tablet",
        "gaming console",
        "wifi router",
    ),
    "Clothing": (
        "cotton kurta",
        "denim jeans",
        "running shoes",
        "winter jacket",
        "saree",
        "formal shirt",
        "sports t-shirt",
        "leather belt",
    ),
    "Groceries": (
        "basmati rice",
        "olive oil",
        "organic honey",
        "green tea",
        "protein powder",
        "almond milk",
        "instant noodles",
        "dark chocolate",
    ),
    "Home appliances": (
        "air conditioner",
        "washing machine",
        "microwave oven",
        "vacuum cleaner",
        "water purifier",
        "ceiling fan",
        "induction cooktop",
        "room heater",
    ),
    "Beauty products": (
        "face serum",
        "sunscreen spf 50",
        "hair oil",
        "lipstick",
        "moisturizer",
        "perfume",
        "face wash",
        "beard trimmer",
    ),
    "Books": (
        "fiction novel",
        "ncert textbook",
        "self help book",
        "comic book",
        "cookbook",
        "history book",
        "poetry collection",
        "exam guide",
    ),
    "Furniture": (
        "office chair",
        "study table",
        "sofa set",
        "queen size bed",
        "bookshelf",
        "dining table",
        "wardrobe",
        "mattress",
    ),
    "Automobiles": (
        "electric scooter",
        "car insurance",
        "bike helmet",
        "car tyre",
        "engine oil",
        "car battery",
        "dash cam",
        "bike service",
    ),
    "Travel": (
        "flight tickets",
        "hotel booking",
        "train reservation",
        "bus tickets",
        "holiday package",
        "travel insurance",
        "cab booking",
        "homestay",
    ),
}

INDIAN_CRICKET = (
    "ipl 2025",
    "ipl live score",
    "csk vs mi",
    "rcb vs kkr",
    "india vs australia",
    "world cup 2025",
    "icc rankings",
    "cricket highlights",
    "ms dhoni",
    "virat kohli century",
    "wtc final",
    "t20 world cup",
)

INDIAN_FESTIVALS = (
    "diwali gifts",
    "diwali decoration",
    "holi colours",
    "navratri garba",
    "raksha bandhan gifts",
    "ganesh chaturthi",
    "onam sadhya",
    "pongal recipes",
    "eid special dishes",
    "christmas cake india",
    "republic day parade",
    "independence day speech",
)

INDIAN_EXAMS = (
    "jee main 2025",
    "jee advanced syllabus",
    "neet preparation",
    "upsc prelims",
    "gate cse",
    "cat mock test",
    "cbse board exam",
    "ssc cgl",
    "nda admit card",
    "clat application",
)

INDIAN_ENTERTAINMENT = (
    "bollywood new release",
    "srk movie",
    "pushpa 2",
    "rrr sequel",
    "tamil movie download",
    "telugu blockbuster",
    "netflix india",
    "hotstar subscription",
    "spotify premium india",
    "k-pop india tour",
)

INDIAN_TECH = (
    "jio recharge",
    "airtel 5g",
    "upi payment",
    "paytm wallet",
    "aadhaar update",
    "digilocker",
    "bhim app",
    "phonepe offers",
    "swiggy coupon",
    "zomato gold",
)

DEVICE_MODIFIERS = ("pro", "max", "ultra", "plus", "mini", "2024", "2025")
SHOPPING_MODIFIERS = (
    "price",
    "deals",
    "cheap",
    "online",
    "in india",
    "free delivery",
    "emi",
    "cashback",
)
ACCESSORY_MODIFIERS = ("charger", "case", "screen protector", "review", "unboxing", "warranty")
TECH_MODIFIERS = (
    "for beginners",
    "crash course",
    "example",
    "setup",
    "config",
    "install",
    "fix",
    "tutorial",
)
EXAM_SUFFIXES = (
    "syllabus",
    "preparation",
    "admit card",
    "mock test",
    "application",
    "result",
    "answer key",
)

SHOPPING_QUALIFIERS = ("buy", "best", "top", "cheap", "latest", "compare", "near me")
TECH_QUALIFIERS = ("how to", "what is", "why is", "when is", "where is", "fix", "install", "setup", "config", "example")

IPHONE_MODELS = ("15", "15 pro", "15 pro max", "14", "14 pro", "13")
IPL_TEAMS = ("csk", "mi", "rcb", "kkr", "srh", "gt", "dc", "rr", "pbks", "lsg")

ELECTRONICS_PRODUCTS = (
    "iphone",
    "samsung galaxy",
    "macbook",
    "ipad",
    "airpods",
    "laptop",
    "wireless earbuds",
    "gaming monitor",
    "mechanical keyboard",
)
TECH_PRODUCTS = (
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

ALL_CATEGORY_PRODUCTS = tuple(
    product for products in CATEGORY_PRODUCTS.values() for product in products
)
ALL_CATEGORIES = tuple(CATEGORY_PRODUCTS.keys())
INDIAN_TERMS = (
    INDIAN_CRICKET + INDIAN_FESTIVALS + INDIAN_EXAMS + INDIAN_ENTERTAINMENT + INDIAN_TECH
)
ALL_PRODUCTS = PRODUCTS + ALL_CATEGORY_PRODUCTS


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


def _sample_count(rng: random.Random) -> int:
    """Sample search frequency from a heavy-tailed (power-law) distribution."""
    raw = rng.paretovariate(1.5)
    count = max(1, int(raw * 50))
    return min(count, 10_000_000)


def _pick_category_product(rng: random.Random) -> tuple[str, str]:
    category = rng.choice(ALL_CATEGORIES)
    product = rng.choice(CATEGORY_PRODUCTS[category])
    return category, product


def _build_iphone_query(rng: random.Random) -> str:
    style = rng.randrange(6)
    if style == 0:
        return f"iphone {rng.choice(IPHONE_MODELS)}"
    if style == 1:
        return f"iphone {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} iphone"
    if style == 3:
        model = rng.choice(("15", "15 pro max"))
        return f"iphone {model} {rng.choice(('price', 'review', 'unboxing'))}"
    if style == 4:
        return f"iphone {rng.choice(ACCESSORY_MODIFIERS)}"
    return "iphone"


def _build_ipl_query(rng: random.Random) -> str:
    style = rng.randrange(6)
    if style == 0:
        return "ipl live score"
    if style == 1:
        return "ipl schedule"
    if style == 2:
        return "ipl points table"
    if style == 3:
        team_one, team_two = rng.sample(IPL_TEAMS, 2)
        return f"ipl {team_one} vs {team_two}"
    if style == 4:
        return rng.choice(("ipl 2025", "ipl highlights", "ipl score today"))
    return f"ipl {rng.choice(('highlights', 'score', 'schedule'))}"


def _build_electronics_query(rng: random.Random) -> str:
    product = rng.choice(ELECTRONICS_PRODUCTS)
    style = rng.randrange(4)
    if style == 0:
        return f"{product} {rng.choice(DEVICE_MODIFIERS)}"
    if style == 1:
        return f"{product} {rng.choice(SHOPPING_MODIFIERS)}"
    if style == 2:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product}"
    return f"{product} {rng.choice(ACCESSORY_MODIFIERS)}"


def _build_tech_query(rng: random.Random) -> str:
    product = rng.choice(TECH_PRODUCTS)
    style = rng.randrange(3)
    if style == 0:
        return f"{rng.choice(TECH_QUALIFIERS)} {product}"
    if style == 1:
        return f"{product} {rng.choice(TECH_MODIFIERS)}"
    return f"{product} {rng.choice(('guide', 'cheatsheet', 'walkthrough'))}"


def _build_category_shopping_query(rng: random.Random) -> str:
    category, product = _pick_category_product(rng)
    style = rng.randrange(3)
    if style == 0:
        return f"{category.lower()} {product}"
    if style == 1:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product}"
    return f"{product} {rng.choice(SHOPPING_MODIFIERS)}"


def _build_query(rng: random.Random, pattern: int) -> str:
    if pattern == 0:
        return _build_iphone_query(rng)
    if pattern == 1:
        return _build_electronics_query(rng)
    if pattern == 2:
        return _build_category_shopping_query(rng)
    if pattern == 3:
        return _build_ipl_query(rng)
    if pattern == 4:
        return (
            f"{rng.choice(INDIAN_CRICKET)} "
            f"{rng.choice(('highlights', 'score', 'schedule'))}"
        )
    if pattern == 5:
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {rng.choice(INDIAN_CRICKET)}"
    if pattern == 6:
        return f"{rng.choice(INDIAN_EXAMS)} {rng.choice(EXAM_SUFFIXES)}"
    if pattern == 7:
        return (
            f"{rng.choice(INDIAN_FESTIVALS)} "
            f"{rng.choice(('ideas', 'shopping', 'recipes'))}"
        )
    if pattern == 8:
        return (
            f"{rng.choice(INDIAN_ENTERTAINMENT)} "
            f"{rng.choice(('review', 'trailer', 'tickets'))}"
        )
    if pattern == 9:
        return _build_tech_query(rng)
    if pattern == 10:
        return f"{rng.choice(INDIAN_TECH)} {rng.choice(('offer', 'plan', 'update'))}"
    if pattern == 11:
        category, product = _pick_category_product(rng)
        return f"{rng.choice(SHOPPING_QUALIFIERS)} {product} {category.lower()}"
    if pattern == 12:
        product = rng.choice(ALL_CATEGORY_PRODUCTS)
        return f"{product} {rng.choice(SHOPPING_MODIFIERS)}"
    if pattern == 13:
        return f"{rng.choice(INDIAN_FESTIVALS)} {rng.choice(SHOPPING_MODIFIERS)}"
    if pattern == 14:
        return f"{rng.choice(INDIAN_ENTERTAINMENT)} {rng.choice(SHOPPING_MODIFIERS)}"
    product = rng.choice(ELECTRONICS_PRODUCTS)
    return f"{product} {rng.choice(DEVICE_MODIFIERS)} {rng.choice(SHOPPING_MODIFIERS)}"


def generate_synthetic_queries(target_count: int, seed: int = 42) -> list[tuple[str, int]]:
    """Generate realistic unique search queries with frequency counts."""
    rng = random.Random(seed)
    queries: dict[str, int] = {}
    pattern_count = 15
    max_attempts = target_count * 20
    attempts = 0

    while len(queries) < target_count and attempts < max_attempts:
        attempts += 1
        pattern = rng.randrange(pattern_count)
        query = _build_query(rng, pattern)
        query = " ".join(query.split())
        if query and query not in queries:
            queries[query] = _sample_count(rng)

    if len(queries) < target_count:
        raise RuntimeError(
            f"Could only generate {len(queries)} unique queries; target was {target_count}"
        )

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
