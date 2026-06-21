"""Application configuration constants."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RedisNode:
    name: str
    host: str
    port: int


REDIS_NODES: list[RedisNode] = [
    RedisNode(name="redis-1", host="localhost", port=6379),
    RedisNode(name="redis-2", host="localhost", port=6380),
    RedisNode(name="redis-3", host="localhost", port=6381),
    RedisNode(name="redis-4", host="localhost", port=6382),
]

# Batch worker settings (Phase 5)
BATCH_SIZE: int = 100
BATCH_FLUSH_INTERVAL_SECONDS: float = 10.0

# Cache settings (Phase 3+)
CACHE_TTL_SECONDS: int = 300
CACHE_KEY_PREFIX: str = "suggest:"

# Suggestion API (Phase 4)
MIN_PREFIX_LENGTH: int = 3
SUGGESTION_LIMIT: int = 10

# Database (Phase 1)
DATABASE_PATH: str = "data/queries.db"

# Decay scheduler (Phase 6) — nightly 10% decay (86400s = 24h)
DECAY_INTERVAL_SECONDS: float = 86400.0
DECAY_FACTOR: float = 0.9

# Trending API (Phase 6)
TRENDING_LIMIT: int = 10

# App
APP_HOST: str = "0.0.0.0"
APP_PORT: int = 8000
