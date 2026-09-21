"""
Reactive state management for inguitive.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
from contextlib import contextmanager
from typing import Any, Generic, TypeVar

from inguitive.session import (
    _get_current_session_from_context,
    _get_data_registry,
)

_T = TypeVar("_T")

_LISTENERS_PREFIX = "__listeners__"

# Values set via State.set() from a background-task context (no active HTTP
# request).  These serve as the broadcast / "latest global" value and are also
# the fallback for sessions that have not yet written the key locally.
_global_state_values: dict[str, Any] = {}

# Context variable to track mutated State objects during request handling.
# Each entry is the State/SessionState object itself (not a string key),
# so the trigger handler can read .listeners directly without a name lookup.
_mutated_states = contextvars.ContextVar("mutated_states", default=set())

# Context var that is True while inside a trigger handler's _track_mutations()
# scope. Lets State.set() / SessionState.set() distinguish "called from a
# trigger handler" (auto-propagation handles the push) from "called from a
# background task" (must schedule the SSE push ourselves).
_in_trigger_handler = contextvars.ContextVar("in_trigger_handler", default=False)

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
    Also sets ``_in_trigger_handler`` so ``State.set()`` / ``SessionState.set()``
    know the auto-propagation path will handle the OOB push and they should
    not schedule their own SSE push.
    """
    token_mutations = _mutated_states.set(set())
    token_in_handler = _in_trigger_handler.set(True)
    try:
        yield
    finally:
        _mutated_states.reset(token_mutations)
        _in_trigger_handler.reset(token_in_handler)


def _get_mutated_states() -> set:
    """Return set of State objects mutated during current request.

    Returns:
        Copy of the set of State/SessionState objects that were mutated via
        ``.set()`` within the current ``_track_mutations()`` context.
    """
    return _mutated_states.get().copy()


class State(Generic[_T]):
    """Reactive state container with global (process-wide) scope.

    The value is stored in a process-wide dict, shared across all sessions.
    When mutated inside a trigger handler, the auto-propagation path
    generates OOB updates for the current session's listening components.
    When mutated from a background task, an SSE push broadcasts the update
    to every connected session.

    The ``name`` parameter is required: it becomes the storage key in the
    process-wide dict and in any serializing backend (e.g. ``RedisBackend``).
    A named state (``State(0, "counter")``) keeps the same key across
    process restarts, so the persisted value survives. The name is not
    used for listener resolution — ``listen_to`` takes the state object
    directly.
    """

    def __init__(self, initial_value: _T, name: str):
        self._initial_value = initial_value
        self.name = name
        self._key = name

    def get(self) -> _T:
        """Return the current global value.

        Always reads from the process-wide store; the value is the same
        for every session.
        """
        return _global_state_values.get(self._key, self._initial_value)  # type: ignore[no-any-return]

    def set(self, new_value: _T) -> None:
        """Write a new global value and broadcast the update.

        A global ``State`` is shared across all sessions. When mutated, the
        update is pushed to every connected session's SSE queues (broadcast).
        Inside a trigger handler, the mutation is also tracked so the
        trigger route's auto-propagation renders the OOB update for the
        requesting session immediately in the HTTP response; the broadcast
        then delivers the same update to all other (and the requesting)
        sessions via SSE.
        """
        _global_state_values[self._key] = new_value
        if _in_trigger_handler.get():
            session = _get_current_session_from_context()
            if session is not None:
                _mutated_states.get().add(self)
                session.mark_dirty()
            if _dev_mode_warnings_enabled and not self.listeners:
                logger.warning(
                    "State '%s' was mutated but no component is listening. "
                    "This may indicate a missing 'listen_to' parameter.",
                    self.name or self._key,
                )
        # Always broadcast a global State mutation to every connected session.
        _schedule_sse_push(self._key)

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

    The ``name`` parameter is inherited from :class:`State` and remains
    required — see the :class:`State` docstring for the rationale (stable
    storage key across restarts with a serializing backend).
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
        """Write a new session-scoped value and push to the current session.

        Inside a trigger handler, the value is written to the session's
        isolated data registry and tracked for auto-propagation via the
        trigger route's OOB response (current session only). Outside a
        trigger handler (background task with a session bound via
        contextvars), the value is written and an SSE push is scheduled
        to the current session's queues only — not a broadcast. When no
        session is bound at all, the value is stored as a global fallback
        and a broadcast is scheduled (edge case).
        """
        session = _get_current_session_from_context()
        if session is None:
            _global_state_values[self._key] = new_value
            _schedule_sse_push(self._key)
            return
        session.data_registry[self._key] = new_value
        session.mark_dirty()
        if _in_trigger_handler.get():
            _mutated_states.get().add(self)
        else:
            # Background task with a session bound: push to this session only.
            _schedule_sse_push_for_session(self._key, session.session_id)
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


def _schedule_sse_push_for_session(state_key: str, session_id: str) -> None:
    """Schedule an async SSE push to a single session's queues.

    Like :func:`_schedule_sse_push` but targets only one session (for
    ``SessionState.set()`` from a background task). No-op when there is no
    running event loop.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_push_sse_for_session_state(state_key, session_id))
    except RuntimeError:
        pass  # No running event loop — SSE push is not possible.


async def _push_sse_for_session_state(state_key: str, session_id: str) -> None:
    """Push OOB HTML for *state_key* to a single session's SSE queues.

    Same rendering logic as :func:`_push_sse_for_state` but limited to one
    session — used by ``SessionState.set()`` from a background task so the
    update reaches only that session's open tabs, not every connected session.
    """
    from inguitive.htmx import update_components
    from inguitive.session import (
        _hydrate_component_registry,
        _get_sse_queues,
        _put_bounded,
        _set_current_session,
        get_session_backend,
    )

    queues = _get_sse_queues(session_id)
    if not queues:
        return

    backend = get_session_backend()
    session = await backend.get_session(session_id)
    if session is None:
        return

    _hydrate_component_registry(session)

    listeners_key = f"{_LISTENERS_PREFIX}{state_key}"
    listeners: set[str] = set(session.data_registry.get(listeners_key, set()))
    if not listeners:
        return

    def _render(s=session, ids=listeners) -> str:
        _set_current_session(s)
        return update_components(*ids)

    html = contextvars.copy_context().run(_render)
    if html:
        for queue in set(queues):
            _put_bounded(queue, html)


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
