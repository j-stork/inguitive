"""
Session management with pluggable backends for inguitive.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
        """Serialize session data for storage.

        Listener sets (``__listeners__*`` keys) are converted to sorted lists
        so the payload is JSON-serialisable for backends like Redis.
        """
        data_registry = {
            key: sorted(value) if isinstance(value, set) else value
            for key, value in self.data_registry.items()
        }
        return {
            "session_id": self.session_id,
            "data_registry": data_registry,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: SessionData) -> Session:
        """Deserialize session data from storage.

        Listener lists (``__listeners__*`` keys) are restored to sets.
        """
        data_registry = dict(data.get("data_registry", {}))
        for key, value in data_registry.items():
            if key.startswith("__listeners__") and isinstance(value, list):
                data_registry[key] = set(value)
        return cls(
            session_id=data["session_id"],
            component_registry={},
            state_registry={},
            data_registry=data_registry,
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
        _evict_component_registry_cache(session_id)

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


@asynccontextmanager
async def session_context(session_id: str) -> AsyncIterator[Session | None]:
    """Bind a session into the current context for the duration of the block.

    This is the background-task analog of the request middleware: it loads the
    session from the backend, restores its live component registry, makes it
    the active session so that ``State.get()`` / ``State.set()`` operate on
    this session's isolated data, and persists the session on exit if it was
    mutated. Use it to run per-session logic outside an HTTP request.

    The yielded value is ``None`` when the session no longer exists (e.g. it
    was evicted or the tab closed and the TTL elapsed); callers should treat
    that as a signal to stop any loop bound to that session.

    Example::

        async with session_context(session_id) as session:
            if session is None:
                return
            counter_state.set(counter_state.get() + 1)
            ids = list(counter_state.listeners)
        await push_update(session_id, *ids)

    Note: ``push_update`` reloads the session from the backend before
    rendering, so it must run *after* the context exits — the save performed
    on exit is what makes the new state visible to the push. Listener IDs
    must be captured *inside* the context, since ``State.listeners`` reads
    the active session's registry.

    Concurrent mutation of the same session (e.g. a background task and a
    concurrent request handler) is last-save-wins; guard against it in your
    app logic if needed.
    """
    # Deferred import: state.py imports from this module at load time.
    from inguitive.state import _track_mutations

    backend = get_session_backend()
    session = await backend.get_session(session_id)
    if session is None:
        yield None
        return

    _hydrate_component_registry(session)
    _set_current_session(session)
    try:
        with _track_mutations():
            yield session
    finally:
        if session._dirty:
            await backend.save_session(session)
            session.clear_dirty()
        _clear_current_session()


# ---------------------------------------------------------------------------
# SSE connection registry
# ---------------------------------------------------------------------------

# Maximum number of pending SSE messages per tab.  When the queue is full
# (slow / stalled consumer), _put_bounded drops the oldest entry before
# adding the new one, so the client always receives the latest state rather
# than stale intermediate values.  This bounds memory regardless of how
# many pushes accumulate while a tab is backpressured.
_SSE_QUEUE_MAX: int = 32

# Maps session_id → set of asyncio.Queue[str].
# One entry per open browser tab — each tab has its own queue so that a
# user with two tabs receives pushes on both, and closing one tab removes
# only that tab's queue without affecting the others.
_sse_connections: dict[str, set[asyncio.Queue]] = {}


def _put_bounded(queue: asyncio.Queue, item: str) -> None:
    """Put *item* into *queue*, applying a drop-oldest backpressure policy.

    If the queue is at capacity, the oldest (most stale) pending update is
    discarded before the new item is enqueued.  This keeps memory bounded and
    ensures a slow or stalled consumer always sees the *latest* state when it
    eventually drains the queue.

    Never blocks — safe to call from any synchronous or asynchronous context.

    Args:
        queue: The target SSE queue (must have a finite ``maxsize``).
        item: The HTML fragment to enqueue.
    """
    try:
        queue.put_nowait(item)
    except asyncio.QueueFull:
        # Discard the oldest stale update to make room.
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        # Re-attempt after freeing one slot.
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            pass  # Genuinely stuck — skip this update rather than blocking.


def _register_sse_connection(session_id: str) -> asyncio.Queue:
    """Create and register a bounded asyncio Queue for one SSE stream.

    Each call returns a *fresh* queue, so multiple open tabs for the same
    session each get their own independent queue.  Call this whenever the
    browser opens ``GET /_sse``; store the returned queue and pass it back
    to :func:`_unregister_sse_connection` when the stream closes.

    Args:
        session_id: Session to register.

    Returns:
        A fresh bounded ``asyncio.Queue`` (capacity :data:`_SSE_QUEUE_MAX`)
        bound to this tab's SSE stream.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    _sse_connections.setdefault(session_id, set()).add(queue)
    return queue


def _unregister_sse_connection(session_id: str, queue: asyncio.Queue) -> None:
    """Remove one specific SSE queue when its client disconnects.

    Only the exact *queue* object is removed.  Other queues for the same
    session (i.e. other open tabs) are left intact.  The session entry is
    removed from the registry only when its last queue is gone.

    Safe to call even if the session has no registered queues.

    Args:
        session_id: Session the stream belongs to.
        queue: The exact queue object returned by :func:`_register_sse_connection`.
    """
    queues = _sse_connections.get(session_id)
    if queues is None:
        return
    queues.discard(queue)
    if not queues:
        _sse_connections.pop(session_id, None)


def _get_sse_queues(session_id: str) -> set[asyncio.Queue]:
    """Return all active SSE queues for *session_id* (one per open tab).

    Returns an empty set when the session has no active SSE connections.

    Args:
        session_id: Session to look up.

    Returns:
        A snapshot set of queues; iterate it to fan out a push.
    """
    return set(_sse_connections.get(session_id, set()))


# ---------------------------------------------------------------------------
# Process-local component-registry cache
# ---------------------------------------------------------------------------

# Live Component objects cannot be serialised to external session stores
# (they hold arbitrary callables), so backends like RedisBackend persist only
# ``data_registry``.  To keep SSE rendering working with such backends, each
# worker caches the live ``component_registry`` of every session it renders,
# keyed by session_id.  Any session with an SSE connection in this worker
# necessarily loaded its page through this worker, so the cache always holds
# the components needed to render pushes for locally-connected clients.
#
# Entries are (registry, last_touched) pairs; stale entries are pruned
# opportunistically using _COMPONENT_CACHE_TTL.
_COMPONENT_CACHE_TTL: float = 3600.0

_component_registry_cache: dict[str, tuple[dict[str, Any], float]] = {}


def _cache_component_registry(session: Session) -> None:
    """Cache a session's live component registry in this worker process.

    Called after each request that rendered components.  A no-op when the
    session's ``component_registry`` is empty (e.g. ``GET /_sse``), so an
    existing cache entry is never clobbered by a render-free request.

    Args:
        session: The session whose live components should be cached.
    """
    if not session.component_registry:
        return
    _component_registry_cache[session.session_id] = (
        session.component_registry,
        time.time(),
    )
    _prune_component_registry_cache()


def _hydrate_component_registry(session: Session) -> None:
    """Populate an empty ``component_registry`` from the process-local cache.

    Backends that serialise sessions (e.g. RedisBackend) return sessions with
    an empty ``component_registry``.  This restores the live components cached
    when this worker last rendered the session's page, enabling SSE pushes to
    re-render components.  A no-op when the registry is already populated
    (MemoryBackend) or when nothing is cached for the session.

    Args:
        session: A session freshly loaded from the backend.
    """
    if session.component_registry:
        return
    entry = _component_registry_cache.get(session.session_id)
    if entry is not None:
        registry, _ = entry
        session.component_registry = registry
        # Refresh the timestamp — the session is clearly still active.
        _component_registry_cache[session.session_id] = (registry, time.time())


def _evict_component_registry_cache(session_id: str) -> None:
    """Remove a session's cached component registry (e.g. on session delete)."""
    _component_registry_cache.pop(session_id, None)


def _prune_component_registry_cache() -> None:
    """Drop cache entries not touched within _COMPONENT_CACHE_TTL."""
    cutoff = time.time() - _COMPONENT_CACHE_TTL
    stale = [sid for sid, (_, touched) in _component_registry_cache.items() if touched < cutoff]
    for sid in stale:
        _component_registry_cache.pop(sid, None)


# ---------------------------------------------------------------------------
# Convenience functions for registries
# ---------------------------------------------------------------------------

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
