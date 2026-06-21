"""Redis cache manager with thundering herd protection (Phase 3)."""

from __future__ import annotations

import asyncio
import json
import logging
import weakref
from collections.abc import Callable
from pathlib import Path

import redis.asyncio as aioredis

from src.cache.consistent_hash import ConsistentHashRing
from src.config import (
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    REDIS_NODES,
    RedisNode,
    SUGGESTION_LIMIT,
)
from src.database import get_suggestions_by_prefix

Suggestion = tuple[str, int]

logger = logging.getLogger(__name__)


class CacheManager:
    """Distributed prefix cache backed by Redis with lazy DB fill on miss."""

    def __init__(
        self,
        redis_nodes: list[RedisNode] | None = None,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        key_prefix: str = CACHE_KEY_PREFIX,
        suggestion_limit: int = SUGGESTION_LIMIT,
        db_path: str | Path | None = None,
        clients: dict[str, aioredis.Redis] | None = None,
        db_loader: Callable[[str, int, str | Path | None], list[Suggestion]] | None = None,
    ) -> None:
        nodes = redis_nodes if redis_nodes is not None else REDIS_NODES
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix
        self._suggestion_limit = suggestion_limit
        self._db_path = db_path
        self._db_loader = db_loader or get_suggestions_by_prefix
        self._ring = ConsistentHashRing([node.name for node in nodes])
        self._node_by_name = {node.name: node for node in nodes}
        self._clients: dict[str, aioredis.Redis] = clients if clients is not None else {}
        self._owns_clients = clients is None
        self._prefix_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def cache_hits(self) -> int:
        return self._cache_hits

    @property
    def cache_misses(self) -> int:
        return self._cache_misses

    async def connect(self) -> None:
        """Create Redis clients for every configured node."""
        if not self._owns_clients or self._clients:
            return

        for node_name, node in self._node_by_name.items():
            client = aioredis.Redis(
                host=node.host,
                port=node.port,
                decode_responses=True,
            )
            self._clients[node_name] = client
            try:
                await client.ping()
            except Exception as exc:
                logger.warning(
                    "Redis ping failed for node %s (%s:%s): %s",
                    node_name,
                    node.host,
                    node.port,
                    exc,
                )

    async def close(self) -> None:
        """Close Redis clients created by this manager."""
        if not self._owns_clients:
            return

        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()

    def _cache_key(self, prefix: str) -> str:
        return f"{self._key_prefix}{prefix}"

    def _client_for_prefix(self, prefix: str) -> aioredis.Redis:
        node_name = self._ring.get_node(prefix)
        try:
            return self._clients[node_name]
        except KeyError as exc:
            raise RuntimeError(
                f"No Redis client configured for node '{node_name}'"
            ) from exc


    def _get_lock(self, prefix: str) -> asyncio.Lock:
        lock = self._prefix_locks.get(prefix)
        if lock is None:
            lock = asyncio.Lock()
            self._prefix_locks[prefix] = lock
        return lock

    @staticmethod
    def _serialize(data: list[Suggestion]) -> str:
        return json.dumps(data)

    @staticmethod
    def _deserialize(raw: str) -> list[Suggestion]:
        parsed = json.loads(raw)
        return [(str(query), int(count)) for query, count in parsed]

    async def get_suggestions(self, prefix: str) -> list[Suggestion]:
        """Return cached suggestions, filling from SQLite on miss."""
        client = self._client_for_prefix(prefix)
        cache_key = self._cache_key(prefix)

        cached = await client.get(cache_key)
        if cached is not None:
            self._cache_hits += 1
            return self._deserialize(cached)

        self._cache_misses += 1
        lock = self._get_lock(prefix)
        async with lock:
            cached = await client.get(cache_key)
            if cached is not None:
                self._cache_hits += 1
                self._cache_misses -= 1
                return self._deserialize(cached)

            suggestions = await asyncio.to_thread(
                self._db_loader,
                prefix,
                self._suggestion_limit,
                self._db_path,
            )
            await self.set_suggestions(prefix, suggestions)
            return suggestions

    async def set_suggestions(
        self,
        prefix: str,
        data: list[Suggestion],
        ttl: int | None = None,
    ) -> None:
        """Store suggestions for a prefix on the node selected by consistent hashing."""
        client = self._client_for_prefix(prefix)
        cache_key = self._cache_key(prefix)
        ttl_seconds = self._ttl_seconds if ttl is None else ttl
        await client.set(cache_key, self._serialize(data), ex=ttl_seconds)

    def get_node_for_prefix(self, prefix: str) -> str:
        """Return the Redis node name responsible for a prefix."""
        return self._ring.get_node(prefix)

    async def inspect_cache(
        self, prefix: str
    ) -> dict[str, str | bool | int | None]:
        """Return cache routing metadata without filling from the database."""
        node_name = self.get_node_for_prefix(prefix)
        client = self._client_for_prefix(prefix)
        cache_key = self._cache_key(prefix)

        cached = await client.get(cache_key)
        hit = cached is not None
        ttl_remaining: int | None = None
        if hit:
            ttl = await client.ttl(cache_key)
            if ttl >= 0:
                ttl_remaining = ttl

        return {
            "prefix": prefix,
            "node": node_name,
            "cache_key": cache_key,
            "hit": hit,
            "ttl_remaining": ttl_remaining,
        }

    async def invalidate_prefixes(self, query: str) -> None:
        """Delete cache keys for every prefix of the query (lazy invalidation)."""
        if not query:
            return

        keys_by_node: dict[str, list[str]] = {}
        for length in range(1, len(query) + 1):
            prefix = query[:length]
            node_name = self._ring.get_node(prefix)
            keys_by_node.setdefault(node_name, []).append(self._cache_key(prefix))

        if not keys_by_node:
            return

        node_keys = list(keys_by_node.items())
        results = await asyncio.gather(
            *(
                self._clients[node_name].delete(*keys)
                for node_name, keys in node_keys
            ),
            return_exceptions=True,
        )
        for (node_name, _), result in zip(node_keys, results, strict=True):
            if isinstance(result, BaseException):
                node = self._node_by_name[node_name]
                logger.warning(
                    "Cache invalidation failed on node %s (%s:%s): %s",
                    node_name,
                    node.host,
                    node.port,
                    result,
                )

    async def flush_all_suggestion_cache(self) -> None:
        """Delete all suggestion cache keys across every Redis node."""
        pattern = f"{self._key_prefix}*"
        node_items = list(self._clients.items())
        results = await asyncio.gather(
            *(
                self._flush_node_suggestion_keys(node_name, client, pattern)
                for node_name, client in node_items
            ),
            return_exceptions=True,
        )
        for (node_name, _), result in zip(node_items, results, strict=True):
            if isinstance(result, BaseException):
                node = self._node_by_name[node_name]
                logger.warning(
                    "Cache flush failed on node %s (%s:%s): %s",
                    node_name,
                    node.host,
                    node.port,
                    result,
                )

    async def _flush_node_suggestion_keys(
        self,
        node_name: str,
        client: aioredis.Redis,
        pattern: str,
    ) -> None:
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break

    async def invalidate_queries_prefixes(self, queries: list[str]) -> None:
        """Delete cache keys for every prefix of all queries, deduplicated per Redis node."""
        if not queries:
            return

        keys_by_node: dict[str, list[str]] = {}
        seen_keys: set[str] = set()

        for query in queries:
            if not query:
                continue
            for length in range(1, len(query) + 1):
                prefix = query[:length]
                cache_key = self._cache_key(prefix)
                if cache_key in seen_keys:
                    continue
                seen_keys.add(cache_key)
                node_name = self._ring.get_node(prefix)
                keys_by_node.setdefault(node_name, []).append(cache_key)

        if not keys_by_node:
            return

        node_keys = list(keys_by_node.items())
        results = await asyncio.gather(
            *(
                self._clients[node_name].delete(*keys)
                for node_name, keys in node_keys
            ),
            return_exceptions=True,
        )
        for (node_name, _), result in zip(node_keys, results, strict=True):
            if isinstance(result, BaseException):
                node = self._node_by_name[node_name]
                logger.warning(
                    "Cache invalidation failed on node %s (%s:%s): %s",
                    node_name,
                    node.host,
                    node.port,
                    result,
                )

