import asyncio
import logging

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging_config import sanitize_log_message

logger = logging.getLogger(__name__)


class RedisManager:
    """Singleton manager for Redis connection lifecycle."""

    _instance: "RedisManager | None" = None
    _init_lock: asyncio.Lock = asyncio.Lock()
    _client: redis.Redis | None

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
            logger.info("Redis connection initialized: %s", sanitize_log_message(settings.REDIS_URL))

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


# Global singleton instance
redis_manager = RedisManager()
