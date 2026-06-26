import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.redis import redis_manager
from app.modules.data_acquisition.cache import InMemoryCache

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache with JSON serialization and InMemoryCache fallback."""

    def __init__(self, default_ttl: int = 300, key_prefix: str = "") -> None:
        self._default_ttl = default_ttl
        self._prefix = key_prefix
        self._fallback_cache = InMemoryCache(default_ttl=default_ttl)

    def _build_key(self, key: str) -> str:
        """Build Redis key with prefix."""
        return f"ia:{self._prefix}:{key}" if self._prefix else f"ia:{key}"

    async def get(self, key: str) -> Any | None:
        """Get value from Redis, fallback to InMemoryCache on connection error."""
        redis_key = self._build_key(key)
        try:
            client = redis_manager.client
        except RuntimeError:
            logger.warning("Redis not initialized, using InMemoryCache fallback for key: %s", redis_key)
            return self._fallback_cache.get(key)
        try:
            value = await client.get(redis_key)
            if value is not None:
                logger.debug("Redis Cache HIT: %s", redis_key)
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    logger.warning("Redis Cache corrupted data for key %s: %s", redis_key, exc)
                    return None
            logger.debug("Redis Cache MISS: %s", redis_key)
            return None
        except (redis.RedisError, ConnectionError, OSError):
            logger.warning("Redis unavailable, using InMemoryCache fallback for key: %s", redis_key)
            return self._fallback_cache.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in Redis, fallback to InMemoryCache on connection error."""
        redis_key = self._build_key(key)
        ttl_seconds = ttl or self._default_ttl
        try:
            client = redis_manager.client
        except RuntimeError:
            logger.warning("Redis not initialized, using InMemoryCache fallback for key: %s", redis_key)
            self._fallback_cache.set(key, value, ttl)
            return
        try:
            serialized = json.dumps(value)
        except (TypeError, ValueError) as exc:
            logger.error("Redis Cache serialization error for key %s: %s", redis_key, exc)
            self._fallback_cache.set(key, value, ttl)
            return
        try:
            await client.setex(redis_key, ttl_seconds, serialized)
            logger.debug("Redis Cache SET: %s (ttl=%s)", redis_key, ttl_seconds)
        except (redis.RedisError, ConnectionError, OSError):
            logger.warning("Redis unavailable, using InMemoryCache fallback for key: %s", redis_key)
            self._fallback_cache.set(key, value, ttl)

    async def invalidate(self, key: str) -> None:
        """Invalidate key in Redis and fallback cache."""
        redis_key = self._build_key(key)
        try:
            client = redis_manager.client
            await client.delete(redis_key)
            logger.debug("Redis Cache INVALIDATE: %s", redis_key)
        except (redis.RedisError, ConnectionError, OSError, RuntimeError):
            logger.warning("Redis unavailable, skipping invalidate for key: %s", redis_key)
        self._fallback_cache.invalidate(key)


def create_redis_cache(default_ttl: int = 300, key_prefix: str = "") -> RedisCache:
    """Factory function to create a RedisCache instance.

    Args:
        default_ttl: Default TTL in seconds for cache entries.
        key_prefix: Prefix for Redis keys (e.g., "ohlcv", "analysis:result").

    Returns:
        Configured RedisCache instance.
    """
    return RedisCache(default_ttl=default_ttl, key_prefix=key_prefix)
