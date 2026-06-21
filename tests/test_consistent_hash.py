"""Consistent hash ring tests (Phase 2)."""

from collections import Counter

import pytest

from src.cache.consistent_hash import ConsistentHashRing
from src.config import REDIS_NODES

NODE_NAMES = [node.name for node in REDIS_NODES]


@pytest.fixture
def ring() -> ConsistentHashRing:
    return ConsistentHashRing(NODE_NAMES)


def test_get_node_is_consistent(ring: ConsistentHashRing) -> None:
    first = ring.get_node("iph")
    for _ in range(100):
        assert ring.get_node("iph") == first


def test_get_node_returns_configured_node_name(ring: ConsistentHashRing) -> None:
    node = ring.get_node("iph")
    assert node in NODE_NAMES


def test_distribution_is_balanced(ring: ConsistentHashRing) -> None:
    keys = [f"prefix-{index}" for index in range(10_000)]
    counts = Counter(ring.get_node(key) for key in keys)

    assert set(counts) == set(NODE_NAMES)

    values = list(counts.values())
    average = sum(values) / len(NODE_NAMES)
    spread = max(values) - min(values)

    assert spread < 0.2 * average


def test_empty_nodes_raises() -> None:
    with pytest.raises(ValueError, match="At least one node"):
        ConsistentHashRing([])
