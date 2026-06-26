import asyncio
import logging
from typing import Optional

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Singleton manager for Redis connection lifecycle."""

    _instance: Optional["RedisManager"] = None
    _init_lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "RedisManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance

    async def initialize(self) -> None:
        """Create Redis client with connection pool (idempotent, thread-safe)."""
        async with self._init_lock:
            if self._client is not None:
                return
            settings = get_settings()
            password = settings.REDIS_PASSWORD or None
            self._client = redis.Redis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                password=password,
            )
            logger.info("Redis connection initialized: %s", _mask_url(settings.REDIS_URL))

    async def close(self) -> None:
        """Close Redis connection gracefully."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client

    async def health_check(self) -> bool:
        """Check if Redis is reachable."""
        if self._client is None:
            return False
        try:
            await self._client.ping()
            return True
        except redis.RedisError:
            return False

    async def reset(self) -> None:
        """Reset singleton state (for testing only)."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        RedisManager._instance = None
        # Recreate lock to avoid "Future attached to a different loop" in tests
        RedisManager._init_lock = asyncio.Lock()


def _mask_url(url: str) -> str:
    """Mask password in Redis URL for safe logging."""
    if "://" not in url:
        return url
    protocol, rest = url.split("://", 1)
    if "@" in rest:
        credentials, host_part = rest.rsplit("@", 1)
        if ":" in credentials:
            user, _ = credentials.split(":", 1)
            return f"{protocol}://{user}:***@{host_part}"
    return url


# Global singleton instance
redis_manager = RedisManager()
