"""Consistent hash ring for Redis node selection (Phase 2)."""

import bisect
import hashlib


class ConsistentHashRing:
    """Maps keys to physical nodes via a sorted ring of virtual node hashes."""

    def __init__(self, nodes: list[str], vnodes_per_node: int = 150) -> None:
        if not nodes:
            raise ValueError("At least one node is required")

        ring: list[tuple[int, str]] = []
        for node in nodes:
            for vnode_index in range(vnodes_per_node):
                vnode_key = f"{node}:{vnode_index}"
                ring.append((self._hash(vnode_key), node))

        ring.sort(key=lambda item: item[0])
        self._ring = ring
        self._hashes = [item[0] for item in ring]

    @staticmethod
    def _hash(key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def get_node(self, key: str) -> str:
        key_hash = self._hash(key)
        index = bisect.bisect_left(self._hashes, key_hash)
        if index == len(self._ring):
            index = 0
        return self._ring[index][1]
