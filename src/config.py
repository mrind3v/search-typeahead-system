"""Application configuration constants."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RedisNode:
    name: str
    host: str
    port: int


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value is not None else default


REDIS_NODES: list[RedisNode] = [
    RedisNode(
        name="redis-1",
        host=os.getenv("REDIS_1_HOST", "localhost"),
        port=_env_int("REDIS_1_PORT", 6379),
    ),
    RedisNode(
        name="redis-2",
        host=os.getenv("REDIS_2_HOST", "localhost"),
        port=_env_int("REDIS_2_PORT", 6380),
    ),
    RedisNode(
        name="redis-3",
        host=os.getenv("REDIS_3_HOST", "localhost"),
        port=_env_int("REDIS_3_PORT", 6381),
    ),
    RedisNode(
        name="redis-4",
        host=os.getenv("REDIS_4_HOST", "localhost"),
        port=_env_int("REDIS_4_PORT", 6382),
    ),
]

# Batch worker settings (Phase 5)
BATCH_SIZE: int = 100
BATCH_FLUSH_INTERVAL_SECONDS: float = 10.0

# Cache settings (Phase 3+)
CACHE_TTL_SECONDS: int = 300
CACHE_KEY_PREFIX: str = "suggest:"

# Suggestion API (Phase 4)
MIN_PREFIX_LENGTH: int = 1
SUGGESTION_LIMIT: int = 10

# Database (Phase 1)
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/queries.db")

# Decay scheduler (Phase 6) — nightly 10% decay (86400s = 24h)
DECAY_INTERVAL_SECONDS: float = 86400.0
DECAY_FACTOR: float = 0.9

# Trending API (Phase 6)
TRENDING_LIMIT: int = 10

# App
APP_HOST: str = "0.0.0.0"
APP_PORT: int = 8000
