"""
Reactive state management for inguitive.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import uuid
from contextlib import contextmanager
from typing import Any, Generic, TypeVar

from inguitive.session import (
    _get_current_session_from_context,
    _get_data_registry,
)

_T = TypeVar("_T")

_LISTENERS_PREFIX = "__listeners__"

_state_name_registry: dict[str, State] = {}

# Values set via State.set() from a background-task context (no active HTTP
# request).  These serve as the broadcast / "latest global" value and are also
# the fallback for sessions that have not yet written the key locally.
_global_state_values: dict[str, Any] = {}

# Context variable to track mutated State objects during request handling.
# Each entry is the State/SessionState object itself (not a string key),
# so the trigger handler can read .listeners directly without a name lookup.
_mutated_states = contextvars.ContextVar("mutated_states", default=set())

# Module-level flag to control dev mode warnings
_dev_mode_warnings_enabled = False

# Module-level logger
logger = logging.getLogger(__name__)


def enable_dev_mode_warnings() -> None:
    """Enable warning when State is mutated with no listeners."""
    global _dev_mode_warnings_enabled
    _dev_mode_warnings_enabled = True


def disable_dev_mode_warnings() -> None:
    """Disable warning when State is mutated with no listeners."""
    global _dev_mode_warnings_enabled
    _dev_mode_warnings_enabled = False


@contextmanager
def _track_mutations():
    """Context manager to track state mutations during handler execution.

    Use this to wrap trigger handler execution. All State.set() calls within
    the context will be recorded and can be retrieved via get_mutated_states().
    """
    token = _mutated_states.set(set())
    try:
        yield
    finally:
        _mutated_states.reset(token)


def _get_mutated_states() -> set:
    """Return set of State objects mutated during current request.

    Returns:
        Copy of the set of State/SessionState objects that were mutated via
        ``.set()`` within the current ``_track_mutations()`` context.
    """
    return _mutated_states.get().copy()


def _get_state_by_name(name: str) -> State | None:
    """Look up a named State object from the global registry."""
    return _state_name_registry.get(name)


class State(Generic[_T]):
    """Reactive state container with global (process-wide) scope.

    The value is stored in a process-wide dict, shared across all sessions.
    When mutated inside a trigger handler, the auto-propagation path
    generates OOB updates for the current session's listening components.
    When mutated from a background task, an SSE push broadcasts the update
    to every connected session.

    Named states (``State(value, "my_state")``) are registered for
    string-based ``listen_to`` lookups (until Task 2.2 switches
    ``listen_to`` to accept State objects directly).
    """

    def __init__(self, initial_value: _T, name: str = ""):
        self._initial_value = initial_value
        self.name = name
        self._key = name if name else f"__anon_{uuid.uuid4().hex}"
        if name:
            _state_name_registry[name] = self

    def get(self) -> _T:
        """Return the current global value.

        Always reads from the process-wide store; the value is the same
        for every session.
        """
        return _global_state_values.get(self._key, self._initial_value)  # type: ignore[no-any-return]

    def set(self, new_value: _T) -> None:
        """Write a new global value and track the mutation.

        Inside a request, the mutation is tracked for auto-propagation
        via the trigger handler's OOB response. Outside a request
        (background task), an SSE push is scheduled to broadcast the
        update to every connected session.
        """
        _global_state_values[self._key] = new_value
        session = _get_current_session_from_context()
        if session is None:
            _schedule_sse_push(self._key)
            return
        _mutated_states.get().add(self)
        session.mark_dirty()
        if _dev_mode_warnings_enabled and not self.listeners:
            logger.warning(
                "State '%s' was mutated but no component is listening. "
                "This may indicate a missing 'listen_to' parameter.",
                self.name or self._key,
            )

    @property
    def listeners(self) -> set[str]:  # type: ignore[valid-type]
        """Return the set of component IDs listening to this state in the active session."""
        listeners_key = f"{_LISTENERS_PREFIX}{self._key}"
        data = _get_data_registry()
        if listeners_key not in data:
            data[listeners_key] = set()
        return data[listeners_key]  # type: ignore[no-any-return]

    def add_listener(self, component_id: str) -> None:
        """Register a component ID as a listener for the active session."""
        self.listeners.add(component_id)  # type: ignore[attr-defined]

    def remove_listener(self, component_id: str) -> None:
        """Remove a component ID from the listeners for the active session."""
        self.listeners.discard(component_id)  # type: ignore[attr-defined]


class SessionState(State[_T]):
    """Reactive state container with per-session scope.

    The value is stored in the session's ``data_registry``, so each
    session maintains fully independent state. When mutated inside a
    trigger handler, the auto-propagation path generates OOB updates
    only for the current session's listening components. When mutated
    from a background task (no active session), the value is stored as
    a global fallback and an SSE push is scheduled.
    """

    def get(self) -> _T:
        """Return the current value for the active session.

        Falls back to the global broadcast value (if set from a
        background task) and then to the initial value when the session
        has no local value.
        """
        session = _get_current_session_from_context()
        if session is None:
            return _global_state_values.get(self._key, self._initial_value)  # type: ignore[no-any-return]
        data = session.data_registry
        if self._key in data:
            return data[self._key]  # type: ignore[no-any-return]
        return _global_state_values.get(self._key, self._initial_value)  # type: ignore[no-any-return]

    def set(self, new_value: _T) -> None:
        """Write a new session-scoped value and track the mutation.

        Inside a request, the value is written to the session's isolated
        data registry. Outside a request (background task), the value
        is stored as a global fallback and an SSE push is scheduled.
        """
        session = _get_current_session_from_context()
        if session is None:
            _global_state_values[self._key] = new_value
            _schedule_sse_push(self._key)
            return
        session.data_registry[self._key] = new_value
        _mutated_states.get().add(self)
        session.mark_dirty()
        if _dev_mode_warnings_enabled and not self.listeners:
            logger.warning(
                "State '%s' was mutated but no component is listening. "
                "This may indicate a missing 'listen_to' parameter.",
                self.name or self._key,
            )


# ---------------------------------------------------------------------------
# SSE push helpers (called by State.set from background-task context)
# ---------------------------------------------------------------------------


def _schedule_sse_push(state_key: str) -> None:
    """Schedule an async SSE push without blocking the caller.

    If there is a running event loop (always true under uvicorn/FastAPI),
    a task is created.  In synchronous contexts (unit tests without a loop)
    this is a no-op.

    Args:
        state_key: The internal key of the mutated State.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_push_sse_for_state(state_key))
    except RuntimeError:
        pass  # No running event loop — SSE push is not possible.


async def _push_sse_for_state(state_key: str) -> None:
    """Push OOB HTML to every SSE-connected tab that listens to *state_key*.

    For each session that has at least one active SSE connection:

    1. Load the session from the backend and, if the backend serialises
       sessions (e.g. ``RedisBackend``, which persists only ``data_registry``),
       restore the live ``component_registry`` from the worker's process-local
       cache.  Any session with an SSE connection in this worker rendered its
       page through this worker, so the cache holds its live components.
    2. Check whether any component in the session listens to this state.
    3. Render the listening components as OOB HTML in an isolated context.
    4. Fan out the HTML to **all** open queues for the session (one per tab).

    Args:
        state_key: The internal key of the mutated State.
    """
    # Deferred imports to avoid circular dependencies.
    from inguitive.htmx import update_components
    from inguitive.session import (
        _hydrate_component_registry,
        _put_bounded,
        _set_current_session,
        _sse_connections,
        get_session_backend,
    )

    backend = get_session_backend()
    # Snapshot the dict so we iterate a stable copy while awaiting.
    for session_id, queues in list(_sse_connections.items()):
        if not queues:
            continue
        try:
            session = await backend.get_session(session_id)
            if session is None:
                continue

            # Restore live components for serialising backends (RedisBackend).
            _hydrate_component_registry(session)

            # Check whether any component in this session listens to the state.
            listeners_key = f"{_LISTENERS_PREFIX}{state_key}"
            listeners: set[str] = set(session.data_registry.get(listeners_key, set()))
            if not listeners:
                continue

            # Render OOB HTML in a copy of the current context with this
            # session active.  Changes to ContextVars inside copy_context().run()
            # are local to that call and do not affect the outer context.
            def _render(s=session, ids=listeners) -> str:
                _set_current_session(s)
                return update_components(*ids)

            html = contextvars.copy_context().run(_render)
            if html:
                # Fan out to every open tab for this session.
                for queue in set(queues):  # snapshot in case set changes
                    _put_bounded(queue, html)
        except Exception:
            # Log and continue — never let one session's failure block others.
            logger.warning(
                "SSE fanout failed for session %r state key %r",
                session_id,
                state_key,
                exc_info=True,
            )
