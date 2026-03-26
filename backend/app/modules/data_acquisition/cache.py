import logging
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class InMemoryCache:
    """In-memory TTL cache backed by cachetools."""

    def __init__(self, default_ttl: int = 300, maxsize: int = 256) -> None:
        self._default_ttl = default_ttl
        self._maxsize = maxsize
        self._cache: TTLCache[str, object] = TTLCache(maxsize=maxsize, ttl=default_ttl)

    def get(self, key: str) -> Any | None:
        value = self._cache.get(key)
        if value is not None:
            logger.debug("Cache HIT: %s", key)
        else:
            logger.debug("Cache MISS: %s", key)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        # cachetools TTLCache uses a single global TTL; for per-key TTL
        # we store items in the shared cache (the global TTL still governs eviction).
        # For truly different TTLs, we use separate cache instances via CachedDataService.
        self._cache[key] = value
        logger.debug("Cache SET: %s (ttl=%s)", key, ttl or self._default_ttl)

    def invalidate(self, key: str) -> None:
        try:
            del self._cache[key]
            logger.debug("Cache INVALIDATE: %s", key)
        except KeyError:
            pass


def make_cache_key(symbol: str, timeframe: str, period: str) -> str:
    """Build a deterministic cache key from query parameters."""
    return f"ohlcv:{symbol.upper()}:{timeframe}:{period}"
