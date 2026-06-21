"""Tests for synthetic query generation in scripts/load_data.py."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.load_data import generate_synthetic_queries

VARIANT_SUFFIX = re.compile(r"\bvariant\s+\d+\b")
FORBIDDEN_NOISE_SUFFIX = re.compile(
    r"\b(live score|unboxing|warranty|score)\s+\d{1,4}$"
)
IPL_ECOMMERCE_TERMS = frozenset(
    {"warranty", "unboxing", "variant", "emi", "cashback", "free delivery"}
)
IPHONE_MODEL_PATTERN = re.compile(r"^iphone (1[3-5]|15 pro max)( |$)")
IPHONE_SHOPPING_PATTERN = re.compile(
    r"^(iphone (price|deals|cheap|online|cashback|review|unboxing|charger|case)|"
    r"(buy|best|cheap|top|latest) iphone)"
)
IPL_EXPECTED = frozenset(
    {
        "ipl live score",
        "ipl schedule",
        "ipl points table",
        "ipl srh vs mi",
        "ipl csk vs gt",
    }
)


@pytest.fixture
def sample_queries() -> list[tuple[str, int]]:
    return generate_synthetic_queries(500, seed=42)


def test_generate_synthetic_queries_is_deterministic() -> None:
    first = generate_synthetic_queries(200, seed=7)
    second = generate_synthetic_queries(200, seed=7)
    assert first == second


def test_generate_synthetic_queries_returns_unique_queries_with_counts() -> None:
    rows = generate_synthetic_queries(100, seed=1)
    queries = [query for query, _ in rows]
    counts = [count for _, count in rows]

    assert len(queries) == len(set(queries))
    assert all(count >= 1 for count in counts)


def test_no_variant_suffix_or_noise_number_combos(
    sample_queries: list[tuple[str, int]],
) -> None:
    for query, _ in sample_queries:
        assert VARIANT_SUFFIX.search(query) is None
        assert FORBIDDEN_NOISE_SUFFIX.search(query) is None


def test_no_ipl_queries_with_ecommerce_modifiers(sample_queries: list[tuple[str, int]]) -> None:
    for query, _ in sample_queries:
        if "ipl" not in query:
            continue
        words = set(query.split())
        assert words.isdisjoint(IPL_ECOMMERCE_TERMS), query


def test_no_cross_domain_book_or_cloud_warranty_combos(
    sample_queries: list[tuple[str, int]],
) -> None:
    for query, _ in sample_queries:
        if "warranty" not in query:
            continue
        lowered = query.lower()
        assert not any(
            term in lowered for term in ("history book", "aws lambda", "fiction novel")
        ), query


def test_includes_realistic_iphone_queries(sample_queries: list[tuple[str, int]]) -> None:
    iphone_queries = [query for query, _ in sample_queries if query.startswith("iphone") or query.endswith(" iphone")]
    assert iphone_queries
    assert any(IPHONE_MODEL_PATTERN.match(query) for query in iphone_queries)
    assert any(IPHONE_SHOPPING_PATTERN.match(query) for query in iphone_queries)


def test_includes_realistic_ipl_queries() -> None:
    queries = {query for query, _ in generate_synthetic_queries(2000, seed=99)}
    assert IPL_EXPECTED.issubset(queries)
