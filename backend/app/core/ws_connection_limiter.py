"""WebSocket per-IP connection limiter with Redis-backed shared state.

This module tracks active WebSocket connections per client IP to enforce a
maximum number of concurrent connections and to prevent memory exhaustion
(Denial of Service via unbounded in-memory growth).

State is stored in Redis so that the limit is enforced across multiple
workers (e.g. gunicorn with several workers). Each connection entry carries
its own expiry timestamp; a background-free TTL guarantees that stale entries
are reclaimed even if a worker crashes or a client disconnects without
triggering the cleanup path. When Redis is unavailable the limiter degrades
gracefully to an in-process store (single-worker semantics only).
"""

import asyncio
import logging
import time

import redis.asyncio as redis
from redis.commands.core import AsyncScript

from app.core.config import get_settings
from app.core.redis import _mask_url, redis_manager

logger = logging.getLogger(__name__)

# Redis key namespace for per-IP WebSocket connection tracking.
_WS_CONN_KEY_PREFIX = "ia:ws:conn"

# Buffer added to the per-key EXPIRE so the hash survives slightly longer than
# the longest possible entry lifetime, avoiding premature deletion of live
# connections while still bounding memory on the Redis side.
_KEY_EXPIRE_BUFFER_SECONDS = 60

# Atomic acquire: prune expired entries, reject when at capacity, otherwise
# register the connection with its absolute expiry timestamp.
# KEYS[1] = hash key
# ARGV[1] = now (seconds, wall clock)
# ARGV[2] = entry ttl (seconds)
# ARGV[3] = max connections per IP
# ARGV[4] = connection id
# ARGV[5] = hash key ttl (entry ttl + buffer)
_ACQUIRE_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local entry_ttl = tonumber(ARGV[2])
local max_conn = tonumber(ARGV[3])
local conn_id = ARGV[4]
local key_ttl = tonumber(ARGV[5])

-- Prune expired entries. HGETALL returns a flat array
-- {field1, val1, field2, val2, ...}; values hold absolute expiry timestamps.
local entries = redis.call('HGETALL', key)
local expired = {}
for i = 1, #entries, 2 do
    if tonumber(entries[i + 1]) < now then
        table.insert(expired, entries[i])
    end
end
if #expired > 0 then
    redis.call('HDEL', key, table.unpack(expired))
end

local count = redis.call('HLEN', key)
if count >= max_conn then
    return 0
end

redis.call('HSET', key, conn_id, now + entry_ttl)
redis.call('EXPIRE', key, key_ttl)
return 1
"""

# Atomic release: drop the connection id; delete the hash when empty.
# KEYS[1] = hash key
# ARGV[1] = connection id
_RELEASE_LUA = """
local key = KEYS[1]
local conn_id = ARGV[1]
redis.call('HDEL', key, conn_id)
if redis.call('HLEN', key) == 0 then
    redis.call('DEL', key)
end
return 1
"""


class WebSocketConnectionLimiter:
    """Enforce a per-IP cap on concurrent WebSocket connections.

    The limiter is safe to share as a singleton across the application. It
    prefers a Redis-backed store (shared across workers) and falls back to an
    in-process store when Redis is unreachable.
    """

    def __init__(self) -> None:
        # Settings are read once at construction; changing the limit or TTL
        # requires an application restart. This is acceptable for production
        # (config is fixed per deployment) and keeps the hot path allocation-free.
        self._max_connections: int = get_settings().WS_MAX_CONNECTIONS_PER_IP
        self._ttl_seconds: int = get_settings().WS_CONNECTION_TTL_SECONDS
        self._acquire_script: AsyncScript | None = None
        self._release_script: AsyncScript | None = None
        # In-memory fallback: client_ip -> {conn_id: absolute_expiry}
        self._lock = asyncio.Lock()
        self._memory: dict[str, dict[str, float]] = {}
        # Tracks which backend served each connection so release() only falls
        # back to the in-memory store when acquire() actually used it. This
        # prevents a Redis-acquired entry from leaking when release() hits a
        # transient Redis error after a successful Redis acquire.
        self._memory_conn_ids: set[str] = set()

    def _build_key(self, client_ip: str) -> str:
        return f"{_WS_CONN_KEY_PREFIX}:{client_ip}"

    def _get_scripts(self) -> tuple[AsyncScript, AsyncScript]:
        """Lazily register Lua scripts against the active Redis client."""
        if self._acquire_script is None or self._release_script is None:
            client = redis_manager.client
            self._acquire_script = client.register_script(_ACQUIRE_LUA)
            self._release_script = client.register_script(_RELEASE_LUA)
        return self._acquire_script, self._release_script

    async def acquire(self, client_ip: str, conn_id: str) -> bool:
        """Attempt to register a new connection for ``client_ip``.

        Returns ``True`` if the connection is allowed (under the per-IP cap and
        not expired), ``False`` if the cap is reached. On Redis failure the
        call degrades to the in-process store so availability is preserved.
        """
        try:
            acquire_script, _ = self._get_scripts()
            key = self._build_key(client_ip)
            now = time.time()
            key_ttl = self._ttl_seconds + _KEY_EXPIRE_BUFFER_SECONDS
            result = await acquire_script(
                keys=[key],
                args=[now, self._ttl_seconds, self._max_connections, conn_id, key_ttl],
            )
            return bool(int(result))
        except (RuntimeError, redis.RedisError, OSError) as exc:
            logger.warning(
                "Redis unavailable for WebSocket limiter, using in-memory fallback: %s",
                _mask_url(str(exc)),
            )
            return await self._acquire_memory(client_ip, conn_id)

    async def release(self, client_ip: str, conn_id: str) -> None:
        """Remove a connection from tracking (called on disconnect/cleanup)."""
        # Only fall back to the in-memory store if this connection was actually
        # acquired there; otherwise a transient Redis error after a successful
        # Redis acquire would drop the entry from the wrong store and leak it.
        if conn_id in self._memory_conn_ids:
            await self._release_memory(client_ip, conn_id)
            return
        try:
            _, release_script = self._get_scripts()
            key = self._build_key(client_ip)
            await release_script(keys=[key], args=[conn_id])
        except (RuntimeError, redis.RedisError, OSError) as exc:
            logger.warning(
                "Redis unavailable for WebSocket limiter, release skipped (entry expires via TTL): %s",
                _mask_url(str(exc)),
            )

    async def _acquire_memory(self, client_ip: str, conn_id: str) -> bool:
        """In-process acquire used when Redis is unavailable."""
        async with self._lock:
            now = time.time()
            connections = self._memory.get(client_ip, {})
            connections = {cid: expiry for cid, expiry in connections.items() if expiry >= now}
            if len(connections) >= self._max_connections:
                logger.warning(
                    "WebSocket rate limited (in-memory): IP %s has %d connections",
                    client_ip,
                    len(connections),
                )
                self._memory[client_ip] = connections
                return False
            connections[conn_id] = now + self._ttl_seconds
            self._memory[client_ip] = connections
            self._memory_conn_ids.add(conn_id)
            return True

    async def _release_memory(self, client_ip: str, conn_id: str) -> None:
        """In-process release used when Redis is unavailable."""
        async with self._lock:
            connections = self._memory.get(client_ip)
            if connections is None:
                return
            connections.pop(conn_id, None)
            self._memory_conn_ids.discard(conn_id)
            if not connections:
                del self._memory[client_ip]


# Module-level singleton reused by the WebSocket endpoint.
ws_connection_limiter = WebSocketConnectionLimiter()
