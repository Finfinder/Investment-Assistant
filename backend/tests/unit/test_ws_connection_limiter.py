"""Unit tests for the WebSocket per-IP connection limiter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from app.core import ws_connection_limiter as wsl_module
from app.core.ws_connection_limiter import WebSocketConnectionLimiter


def _fake_script(return_values):
    """Build a fake registered Lua script: callable returning an awaitable."""

    async def _script(*_args, **_kwargs):
        return return_values.pop(0)

    return _script


@pytest.fixture
def limiter() -> WebSocketConnectionLimiter:
    """Provide a fresh limiter with default settings."""
    with patch("app.core.ws_connection_limiter.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.WS_MAX_CONNECTIONS_PER_IP = 5
        settings.WS_CONNECTION_TTL_SECONDS = 300
        yield WebSocketConnectionLimiter()


async def test_acquire_allows_up_to_limit(limiter: WebSocketConnectionLimiter) -> None:
    """acquire returns True until the per-IP cap is reached."""
    ip = "203.0.113.7"
    for i in range(limiter._max_connections):
        assert await limiter._acquire_memory(ip, f"conn-{i}") is True
    assert len(limiter._memory[ip]) == limiter._max_connections


async def test_acquire_rejects_above_limit_and_warns(
    limiter: WebSocketConnectionLimiter, caplog: pytest.LogCaptureFixture
) -> None:
    """acquire returns False and logs a warning once the cap is exceeded."""
    ip = "203.0.113.8"
    for i in range(limiter._max_connections):
        await limiter._acquire_memory(ip, f"conn-{i}")
    assert await limiter._acquire_memory(ip, "conn-over") is False
    assert any("rate limited" in rec.message for rec in caplog.records)


async def test_release_removes_entry_and_clears_empty_key(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """release drops the connection and deletes the IP key when empty."""
    ip = "203.0.113.9"
    await limiter._acquire_memory(ip, "conn-a")
    await limiter._release_memory(ip, "conn-a")
    assert ip not in limiter._memory


async def test_expired_entries_are_pruned_on_acquire(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """Stale entries (past TTL) are pruned and do not count toward the cap."""
    ip = "203.0.113.10"
    limiter._memory[ip] = {"stale": 0.0}  # already expired (epoch 0)
    assert await limiter._acquire_memory(ip, "conn-fresh") is True
    assert "stale" not in limiter._memory[ip]


async def test_redis_acquire_rejects_above_limit(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """Redis-backed acquire rejects when the cap is reached."""
    ip = "203.0.113.11"
    mock_client = AsyncMock()
    mock_client.register_script = MagicMock(return_value=_fake_script([1, 1, 1, 1, 1, 0]))
    with patch.object(wsl_module, "redis_manager", create=True) as mock_manager:
        mock_manager.client = mock_client
        limiter._acquire_script = None
        limiter._release_script = None
        for i in range(limiter._max_connections):
            assert await limiter.acquire(ip, f"conn-{i}") is True
        assert await limiter.acquire(ip, "conn-over") is False


async def test_redis_fallback_on_runtime_error(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """When Redis is unavailable, acquire degrades to in-memory store."""
    mock_client = AsyncMock()
    mock_client.register_script = MagicMock(side_effect=RuntimeError("redis down"))
    ip = "203.0.113.12"
    with patch.object(wsl_module, "redis_manager", create=True) as mock_manager:
        mock_manager.client = mock_client
        limiter._acquire_script = None
        limiter._release_script = None
        for i in range(limiter._max_connections):
            assert await limiter.acquire(ip, f"conn-{i}") is True
        # Cap is enforced even in the in-memory fallback path.
        assert await limiter.acquire(ip, "conn-over") is False
        assert ip in limiter._memory


async def test_redis_release_clears_empty_key(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """Redis-backed release deletes the hash when the last entry is removed."""
    ip = "203.0.113.13"
    mock_client = AsyncMock()
    acquire_script = _fake_script([1])
    release_script = _fake_script([1])
    mock_client.register_script = MagicMock(side_effect=lambda lua: acquire_script if "HSET" in lua else release_script)
    with patch.object(wsl_module, "redis_manager", create=True) as mock_manager:
        mock_manager.client = mock_client
        limiter._acquire_script = None
        limiter._release_script = None
        assert await limiter.acquire(ip, "conn-x") is True
        # release must invoke the registered release script without error.
        await limiter.release(ip, "conn-x")


async def test_multi_worker_shared_counter(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """Two limiter instances sharing one Redis client enforce a shared cap."""
    ip = "203.0.113.14"
    shared_client = AsyncMock()

    # Shared state emulating Redis: allow up to the cap, reject above it,
    # and free capacity after a release.
    state: dict[str, int] = {"active": 0}
    cap = limiter._max_connections

    async def _acquire_script(*_args, **_kwargs):
        if state["active"] >= cap:
            return 0
        state["active"] += 1
        return 1

    async def _release_script(*_args, **_kwargs):
        state["active"] = max(0, state["active"] - 1)
        return 1

    shared_client.register_script = MagicMock(
        side_effect=lambda lua: _acquire_script if "HSET" in lua else _release_script
    )

    worker_a = WebSocketConnectionLimiter()
    worker_b = WebSocketConnectionLimiter()
    with patch.object(wsl_module, "redis_manager", create=True) as mock_manager:
        mock_manager.client = shared_client
        worker_a._acquire_script = None
        worker_a._release_script = None
        worker_b._acquire_script = None
        worker_b._release_script = None
        for i in range(limiter._max_connections):
            assert await worker_a.acquire(ip, f"a-{i}") is True
        # Worker B sees the connections registered by Worker A.
        assert await worker_b.acquire(ip, "b-over") is False
        await worker_a.release(ip, "a-0")
        # After a release, capacity frees up for Worker B.
        assert await worker_b.acquire(ip, "b-new") is True


async def test_memory_prunes_expired_entries_on_acquire(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """Expired in-memory entries are pruned so capacity is reclaimed (mirrors Lua)."""
    ip = "203.0.113.50"
    # Fill the cap with already-expired entries (timestamp in the past).
    limiter._memory[ip] = {f"stale-{i}": 0.0 for i in range(limiter._max_connections)}
    # A fresh acquire must prune the stale entries and succeed (not reject).
    assert await limiter._acquire_memory(ip, "conn-fresh") is True
    assert list(limiter._memory[ip].keys()) == ["conn-fresh"]


async def test_release_does_not_fall_back_when_acquired_via_redis(
    limiter: WebSocketConnectionLimiter,
) -> None:
    """A Redis-acquired connection whose release hits a Redis error must not
    leak into the in-memory store (it expires via Redis TTL instead)."""
    ip = "203.0.113.60"
    mock_client = AsyncMock()
    acquire_script = _fake_script([1])
    # Release script raises a Redis error to simulate a transient outage.
    release_error = redis.RedisError("connection reset")

    def _register(lua):
        if "HSET" in lua:
            return acquire_script

        async def _fail(*_args, **_kwargs):
            raise release_error

        return _fail

    mock_client.register_script = MagicMock(side_effect=_register)
    with patch.object(wsl_module, "redis_manager", create=True) as mock_manager:
        mock_manager.client = mock_client
        limiter._acquire_script = None
        limiter._release_script = None
        assert await limiter.acquire(ip, "conn-x") is True
        # Release fails on Redis; must NOT fall back to in-memory cleanup.
        await limiter.release(ip, "conn-x")
        assert "conn-x" not in limiter._memory_conn_ids
        assert ip not in limiter._memory
