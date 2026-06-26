"""Tests for RedisManager singleton."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as redis

from app.core.redis import RedisManager


@pytest.fixture(autouse=True)
def reset_redis_manager():
    """Reset RedisManager singleton state before each test."""
    RedisManager._instance = None
    RedisManager._init_lock = asyncio.Lock()
    yield
    RedisManager._instance = None
    RedisManager._init_lock = asyncio.Lock()


def test_singleton_pattern() -> None:
    """RedisManager should be a singleton."""
    manager1 = RedisManager()
    manager2 = RedisManager()
    assert manager1 is manager2


async def test_initialize_creates_redis_client() -> None:
    """initialize() should create Redis client with connection pool."""
    manager = RedisManager()

    with patch("app.core.redis.redis.Redis.from_url") as mock_from_url:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        await manager.initialize()

        mock_from_url.assert_called_once()
        assert manager._client is mock_client


async def test_close_closes_connection() -> None:
    """close() should close Redis connection gracefully."""
    manager = RedisManager()
    mock_client = AsyncMock()
    manager._client = mock_client

    await manager.close()

    mock_client.close.assert_called_once()
    assert manager._client is None


async def test_health_check_returns_true_when_connected() -> None:
    """health_check() should return True when Redis is reachable."""
    manager = RedisManager()
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    manager._client = mock_client

    result = await manager.health_check()

    assert result is True


async def test_health_check_returns_false_when_disconnected() -> None:
    """health_check() should return False when Redis is unreachable."""
    manager = RedisManager()
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(side_effect=redis.RedisError("Connection refused"))
    manager._client = mock_client

    result = await manager.health_check()

    assert result is False


def test_client_raises_when_not_initialized() -> None:
    """client property should raise RuntimeError when not initialized."""
    manager = RedisManager()
    manager._client = None

    with pytest.raises(RuntimeError, match="Redis client not initialized"):
        _ = manager.client


async def test_reset_clears_singleton() -> None:
    """reset() should clear singleton state."""
    manager = RedisManager()
    manager._client = AsyncMock()
    await manager.reset()

    assert manager._client is None
    assert RedisManager._instance is None
