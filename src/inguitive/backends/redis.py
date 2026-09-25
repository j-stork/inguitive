"""
Redis-based session backend for inguitive.

Install with: pip install inguitive[redis]

Usage:
    from inguitive.backends.redis import RedisBackend
    from inguitive import set_session_backend

    set_session_backend(RedisBackend(redis_url="redis://localhost:6379"))
"""

from __future__ import annotations

import asyncio
import json

from inguitive.session import (
    Session,
    SessionBackend,
    SessionId,
    _evict_component_registry_cache,
)


class RedisBackend(SessionBackend):
    """Redis-based session backend for production.

    Requires the optional ``redis`` package: ``pip install inguitive[redis]``.
    Configure during app initialization::

        from inguitive.backends.redis import RedisBackend
        from inguitive import set_session_backend

        set_session_backend(RedisBackend(redis_url="redis://localhost:6379"))

    Alternatively pass the backend to ``UI(app, session_backend=...)``.
    Sessions are stored JSON-serialized under ``inguitive:session:<id>``
    with a TTL.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 3600, db: int = 0):
        """
        Initialize Redis backend.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Session timeout in seconds (default: 3600 = 1 hour)
            db: Redis database number
        """
        self._redis_url = redis_url
        self._ttl_seconds = ttl_seconds
        self._db = db
        self._client = None
        self._lock = asyncio.Lock()

    async def _get_client(self):
        """Lazy initialization of async Redis client with double-checked locking."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        import redis.asyncio as aioredis

                        self._client = aioredis.Redis.from_url(
                            self._redis_url, db=self._db, decode_responses=True
                        )
                    except ImportError:
                        raise ImportError(
                            "Redis backend requires 'redis' package. Install with: pip install inguitive[redis]"
                        )
        return self._client

    def _make_key(self, session_id: SessionId) -> str:
        """Create Redis key for session."""
        return f"inguitive:session:{session_id}"

    async def get_session(self, session_id: SessionId) -> Session | None:
        """Retrieve session from Redis."""
        client = await self._get_client()
        key = self._make_key(session_id)
        data = await client.get(key)
        if data is None:
            return None
        try:
            session_data = json.loads(data)
            return Session.from_dict(session_data)
        except (json.JSONDecodeError, KeyError):
            # Log error and return None
            return None

    async def save_session(self, session: Session) -> None:
        """Save session to Redis with TTL."""
        client = await self._get_client()
        key = self._make_key(session.session_id)
        data = json.dumps(session.to_dict())
        await client.setex(key, self._ttl_seconds, data)

    async def delete_session(self, session_id: SessionId) -> None:
        """Delete session from Redis."""
        client = await self._get_client()
        key = self._make_key(session_id)
        await client.delete(key)
        _evict_component_registry_cache(session_id)

    async def cleanup_expired(self) -> int:
        """Redis handles TTL automatically. This is a no-op."""
        return 0

    async def aclose(self) -> None:
        """Close the Redis connection asynchronously.

        Use this in async contexts like FastAPI lifespan handlers:
            await backend.aclose()
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
