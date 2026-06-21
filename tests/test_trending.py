"""Trending endpoint tests (Phase 6)."""

from __future__ import annotations

from src.database import bulk_insert_queries


def test_trending_returns_top_queries_ordered_by_count(client, db_path) -> None:
    bulk_insert_queries(
        [
            ("trend alpha", 900),
            ("trend beta", 1200),
            ("trend gamma", 300),
        ],
        db_path,
    )

    response = client.get("/trending")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trending"] == [
        {"query": "trend beta", "count": 1200},
        {"query": "trend alpha", "count": 900},
        {"query": "iphone 15", "count": 500},
        {"query": "iphone 14", "count": 400},
        {"query": "trend gamma", "count": 300},
        {"query": "android phone", "count": 100},
    ]


def test_trending_respects_limit(client, db_path) -> None:
    bulk_insert_queries([(f"query {index}", index) for index in range(20, 0, -1)], db_path)

    response = client.get("/trending?limit=3")

    assert response.status_code == 200
    trending = response.json()["trending"]
    assert len(trending) == 3
    assert trending[0]["count"] >= trending[1]["count"] >= trending[2]["count"]


def test_trending_rejects_invalid_limit(client) -> None:
    response = client.get("/trending?limit=0")
    assert response.status_code == 422
