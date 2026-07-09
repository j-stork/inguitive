"""
Session management with pluggable backends for INGUITIVE.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict

# Type aliases
SessionId = str
SessionData = Dict[str, Any]


@dataclass
class Session:
    """Represents a user session with isolated registries."""

    session_id: SessionId
    component_registry: dict[str, Any] = field(default_factory=dict)
    state_registry: dict[str, Any] = field(default_factory=dict)
    data_registry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> SessionData:
        """Serialize session data for storage."""
        return {
            "session_id": self.session_id,
            "data_registry": self.data_registry,
        }

    @classmethod
    def from_dict(cls, data: SessionData) -> Session:
        """Deserialize session data from storage."""
        return cls(
            session_id=data["session_id"],
            component_registry={},
            state_registry={},
            data_registry=data.get("data_registry", {}),
        )


class SessionBackend(ABC):
    """Abstract base class for session backends."""

    @abstractmethod
    def get_session(self, session_id: SessionId) -> Session | None:
        """Retrieve a session by ID. Returns None if not found."""
        ...

    @abstractmethod
    def save_session(self, session: Session) -> None:
        """Save a session to the backend."""
        ...

    @abstractmethod
    def delete_session(self, session_id: SessionId) -> None:
        """Delete a session from the backend."""
        ...

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Clean up expired sessions. Returns number of sessions deleted."""
        ...


class MemoryBackend(SessionBackend):
    """In-memory session backend for development. Not suitable for production."""

    # Class-level storage shared across all instances
    _sessions: dict[SessionId, Session] = {}

    def __init__(self):
        """Initialize memory backend."""

    def get_session(self, session_id: SessionId) -> Session | None:
        """Retrieve session from memory."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return session

    def save_session(self, session: Session) -> None:
        """Save session to memory."""
        self._sessions[session.session_id] = session

    def delete_session(self, session_id: SessionId) -> None:
        """Delete session from memory."""
        self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Clean up expired sessions.

        Note: MemoryBackend is for development only. Sessions are stored
        in memory and lost on server restart, so explicit TTL-based cleanup
        is not necessary. This method returns 0 and performs no action.
        """
        return 0


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

    def _get_client(self):
        """Lazy initialization of Redis client."""
        if self._client is None:
            try:
                import redis

                self._client = redis.Redis.from_url(self._redis_url, db=self._db, decode_responses=True)
            except ImportError:
                raise ImportError("Redis backend requires 'redis' package. Install with: pip install redis")
        return self._client

    def _make_key(self, session_id: SessionId) -> str:
        """Create Redis key for session."""
        return f"inguitive:session:{session_id}"

    def get_session(self, session_id: SessionId) -> Session | None:
        """Retrieve session from Redis."""
        client = self._get_client()
        key = self._make_key(session_id)
        data = client.get(key)
        if data is None:
            return None
        try:
            session_data = json.loads(data)
            return Session.from_dict(session_data)
        except (json.JSONDecodeError, KeyError):
            # Log error and return None
            return None

    def save_session(self, session: Session) -> None:
        """Save session to Redis with TTL."""
        client = self._get_client()
        key = self._make_key(session.session_id)
        data = json.dumps(session.to_dict())
        client.setex(key, self._ttl_seconds, data)

    def delete_session(self, session_id: SessionId) -> None:
        """Delete session from Redis."""
        client = self._get_client()
        key = self._make_key(session_id)
        client.delete(key)

    def cleanup_expired(self) -> int:
        """Redis handles TTL automatically. This is a no-op."""
        return 0


# Global session backend instance
_session_backend: SessionBackend | None = None

# Context variable for current session ID
_current_session_id: ContextVar[SessionId | None] = ContextVar("current_session_id", default=None)


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


def create_session() -> Session:
    """Create a new session with unique ID."""
    session_id = str(uuid.uuid4())
    return Session(session_id=session_id)


def get_current_session() -> Session | None:
    """Get the current session for this request/context."""
    session_id = _current_session_id.get()
    if session_id is None:
        return None
    backend = get_session_backend()
    return backend.get_session(session_id)


def get_or_create_current_session() -> Session:
    """Get current session or create a new one."""
    session = get_current_session()
    if session is not None:
        return session

    # Create new session
    session = create_session()
    backend = get_session_backend()
    backend.save_session(session)

    # Set in context
    _current_session_id.set(session.session_id)
    return session


def set_current_session(session: Session) -> None:
    """Set the current session for this request/context."""
    _current_session_id.set(session.session_id)


def clear_current_session() -> None:
    """Clear the current session from context."""
    _current_session_id.set(None)


def get_session_id() -> str | None:
    """Get the current session ID, or None if no session is active."""
    session = get_current_session()
    return session.session_id if session else None


# Convenience functions for registries
def get_component_registry() -> dict[str, Any]:
    """Get the component registry for the current session."""
    return get_or_create_current_session().component_registry


def get_state_registry() -> dict[str, Any]:
    """Get the state registry for the current session."""
    return get_or_create_current_session().state_registry


def get_data_registry() -> dict[str, Any]:
    """Get the data registry for the current session."""
    return get_or_create_current_session().data_registry
