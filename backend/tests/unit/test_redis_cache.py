"""Tests for RedisCache with JSON serialization and InMemoryCache fallback."""

from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as redis

from app.modules.data_acquisition.redis_cache import RedisCache


@pytest.fixture
def mock_redis_client():
    """Provide a mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def cache(mock_redis_client) -> RedisCache:
    """Provide a RedisCache with mocked Redis manager."""
    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        mock_manager.client = mock_redis_client
        yield RedisCache(default_ttl=60, key_prefix="test")


async def test_cache_set_and_get(cache: RedisCache, mock_redis_client: AsyncMock) -> None:
    mock_redis_client.get = AsyncMock(return_value=b'{"data": "value1"}')
    await cache.set("key1", {"data": "value1"})
    result = await cache.get("key1")
    assert result == {"data": "value1"}


async def test_cache_miss_returns_none(cache: RedisCache) -> None:
    result = await cache.get("nonexistent")
    assert result is None


async def test_key_prefix_applied(cache: RedisCache) -> None:
    assert cache._build_key("key1") == "ia:test:key1"


async def test_key_without_prefix() -> None:
    no_prefix_cache = RedisCache(default_ttl=60, key_prefix="")
    assert no_prefix_cache._build_key("key1") == "ia:key1"


async def test_invalidate(cache: RedisCache, mock_redis_client: AsyncMock) -> None:
    await cache.invalidate("key1")
    mock_redis_client.delete.assert_called_once()


async def test_serialization_with_list(cache: RedisCache, mock_redis_client: AsyncMock) -> None:
    data = [{"time": "2024-01-01", "close": 1.1}, {"time": "2024-01-02", "close": 1.2}]
    mock_redis_client.get = AsyncMock(
        return_value=b'[{"time": "2024-01-01", "close": 1.1}, {"time": "2024-01-02", "close": 1.2}]'
    )
    await cache.set("ohlcv", data)
    result = await cache.get("ohlcv")
    assert result == data


async def test_fallback_on_redis_error(cache: RedisCache) -> None:
    """When Redis raises RedisError, get() should fallback to InMemoryCache."""
    cache._fallback_cache.set("fallback_key", "fallback_value")

    with (
        patch.object(cache, "_build_key", return_value="ia:test:fallback_key"),
        patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager,
    ):
        mock_manager.client.get = AsyncMock(side_effect=redis.RedisError("Connection refused"))
        result = await cache.get("fallback_key")

    assert result == "fallback_value"


async def test_get_raises_runtime_error_when_not_initialized() -> None:
    """get() should fallback to InMemoryCache when Redis is not initialized."""
    cache = RedisCache(default_ttl=60, key_prefix="test")
    cache._fallback_cache.set("any_key", "fallback_value")

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        type(mock_manager).client = property(lambda self: (_ for _ in ()).throw(RuntimeError("Not initialized")))
        result = await cache.get("any_key")

    assert result == "fallback_value"


async def test_set_fallback_on_redis_error() -> None:
    """set() should fallback to InMemoryCache when Redis raises RedisError."""
    cache = RedisCache(default_ttl=60, key_prefix="test")

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        mock_manager.client.setex = AsyncMock(side_effect=redis.RedisError("Connection refused"))
        await cache.set("fallback_key", "fallback_value")

    assert cache._fallback_cache.get("fallback_key") == "fallback_value"


async def test_set_fallback_when_not_initialized() -> None:
    """set() should fallback to InMemoryCache when Redis is not initialized."""
    cache = RedisCache(default_ttl=60, key_prefix="test")

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        type(mock_manager).client = property(lambda self: (_ for _ in ()).throw(RuntimeError("Not initialized")))
        await cache.set("fallback_key", "fallback_value")

    assert cache._fallback_cache.get("fallback_key") == "fallback_value"


async def test_get_returns_none_on_corrupted_json(cache: RedisCache) -> None:
    """get() should return None when Redis contains corrupted JSON data."""
    cache._fallback_cache.set("corrupted_key", "fallback_value")

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        mock_manager.client.get = AsyncMock(return_value=b"not valid json {{{")
        result = await cache.get("corrupted_key")

    assert result is None


async def test_set_fallback_on_serialization_error() -> None:
    """set() should fallback to InMemoryCache when json.dumps fails."""
    cache = RedisCache(default_ttl=60, key_prefix="test")

    with patch("app.modules.data_acquisition.redis_cache.redis_manager"):
        # Object that cannot be serialized by json.dumps
        import datetime

        unserializable = {"date": datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)}
        await cache.set("date_key", unserializable)

    assert cache._fallback_cache.get("date_key") == unserializable


async def test_set_fallback_on_non_serializable() -> None:
    """set() should fallback to InMemoryCache for non-serializable values."""
    cache = RedisCache(default_ttl=60, key_prefix="test")
    mock_client = AsyncMock()
    mock_client.setex = AsyncMock()

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        mock_manager.client = mock_client
        await cache.set("bad_key", object())

    assert cache._fallback_cache.get("bad_key") is not None


async def test_create_redis_cache_factory() -> None:
    """create_redis_cache() should return RedisCache with correct parameters."""
    from app.modules.data_acquisition.redis_cache import create_redis_cache

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        mock_manager.client = AsyncMock()
        cache = create_redis_cache(default_ttl=120, key_prefix="custom")

    assert cache._default_ttl == 120
    assert cache._prefix == "custom"
