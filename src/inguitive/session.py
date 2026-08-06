"""
Session management with pluggable backends for inguitive.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

# Type aliases
SessionId = str
SessionData = dict[str, Any]


@dataclass
class Session:
    """Represents a user session with isolated registries."""

    session_id: SessionId
    component_registry: dict[str, Any] = field(default_factory=dict)
    state_registry: dict[str, Any] = field(default_factory=dict)
    data_registry: dict[str, Any] = field(default_factory=dict)
    last_accessed: float = field(default_factory=lambda: time.time())
    _dirty: bool = field(default=False)

    def mark_dirty(self) -> None:
        """Mark the session as having unsaved changes."""
        self._dirty = True

    def clear_dirty(self) -> None:
        """Clear the dirty flag after saving."""
        self._dirty = False

    def to_dict(self) -> SessionData:
        """Serialize session data for storage."""
        return {
            "session_id": self.session_id,
            "data_registry": self.data_registry,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: SessionData) -> Session:
        """Deserialize session data from storage."""
        return cls(
            session_id=data["session_id"],
            component_registry={},
            state_registry={},
            data_registry=data.get("data_registry", {}),
            last_accessed=data.get("last_accessed", 0.0),
            _dirty=False,
        )


class SessionBackend(ABC):
    """Abstract base class for session backends."""

    @abstractmethod
    async def get_session(self, session_id: SessionId) -> Session | None:
        """Retrieve a session by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Save a session to the backend."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: SessionId) -> None:
        """Delete a session from the backend."""
        ...

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions. Returns number of sessions deleted."""
        ...


class MemoryBackend(SessionBackend):
    """In-memory session backend for **development only**. NOT SUITABLE FOR PRODUCTION with multiple workers or threads."""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize memory backend.

        Args:
            ttl_seconds: Session timeout in seconds (default: 3600 = 1 hour).
                        Sessions older than this will be cleaned up.
                        Set to 0 or negative for no expiry (not recommended).
        """
        self._sessions: dict[SessionId, Session] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def get_session(self, session_id: SessionId) -> Session | None:
        """Retrieve session from memory."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            # Update last_accessed timestamp on every access
            session.last_accessed = time.time()
            # Reset dirty flag - loaded sessions start clean
            session._dirty = False
            return session

    async def save_session(self, session: Session) -> None:
        """Save session to memory."""
        async with self._lock:
            # Update last_accessed timestamp on every save
            session.last_accessed = time.time()
            self._sessions[session.session_id] = session

    async def delete_session(self, session_id: SessionId) -> None:
        """Delete session from memory."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def cleanup_expired(self) -> int:
        """Clean up expired sessions.

        Removes all sessions that have not been accessed within the TTL period.
        Returns the number of sessions deleted.

        Note: If ttl_seconds is 0 or negative, no sessions are cleaned up.
        """
        async with self._lock:
            if self._ttl_seconds <= 0:
                # No expiry configured
                return 0

            current_time = time.time()
            expiry_threshold = current_time - self._ttl_seconds

            # Collect expired session IDs
            expired_ids = [
                session_id for session_id, session in self._sessions.items() if session.last_accessed < expiry_threshold
            ]

            # Delete expired sessions
            for session_id in expired_ids:
                del self._sessions[session_id]

            return len(expired_ids)


class RedisBackend(SessionBackend):
    """Redis-based session backend for production."""

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
                            "Redis backend requires 'redis' package. Install with: pip install redis"
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


# Global session backend instance
_session_backend: SessionBackend | None = None

# Context variable for current Session object (for direct sync access)
_current_session: ContextVar[Session | None] = ContextVar("current_session", default=None)


def get_session_backend() -> SessionBackend:
    """Get the configured session backend. Defaults to MemoryBackend."""
    global _session_backend
    if _session_backend is None:
        _session_backend = MemoryBackend()
    return _session_backend


def set_session_backend(backend: SessionBackend) -> None:
    """Set the session backend. Call this during app initialization."""
    global _session_backend
    _session_backend = backend


def _create_session() -> Session:
    """Create a new session with unique ID."""
    session_id = str(uuid.uuid4())
    return Session(session_id=session_id)


def _get_current_session_from_context() -> Session | None:
    """Get the current Session object directly from context (no backend calls)."""
    return _current_session.get()


def _get_or_create_current_session() -> Session:
    """Get current session or create a new one.

    This function is used internally by the registry helper functions.
    If no session exists in context, it creates a new one and sets it in context.
    Note: This function does NOT call the backend - the middleware is responsible
    for persisting sessions to the backend.
    """
    session = _get_current_session_from_context()
    if session is not None:
        return session

    # Create new session
    session = _create_session()

    # Set in context (but don't call backend - middleware handles persistence)
    _current_session.set(session)
    return session


def _set_current_session(session: Session) -> None:
    """Set the current session for this request/context."""
    _current_session.set(session)


def _clear_current_session() -> None:
    """Clear the current session from context."""
    _current_session.set(None)


def get_session_id() -> str | None:
    """Get the current session ID, or None if no session is active."""
    session = _get_current_session_from_context()
    return session.session_id if session else None


# Convenience functions for registries
def _get_component_registry() -> dict[str, Any]:
    """Get the component registry for the current session."""
    session = _get_or_create_current_session()
    return session.component_registry


def _get_state_registry() -> dict[str, Any]:
    """Get the state registry for the current session."""
    session = _get_or_create_current_session()
    return session.state_registry


def _get_data_registry() -> dict[str, Any]:
    """Get the data registry for the current session."""
    session = _get_or_create_current_session()
    return session.data_registry
