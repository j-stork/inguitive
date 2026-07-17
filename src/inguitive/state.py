"""
Reactive state management for INGUITIVE.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
import uuid
from typing import Generic, TypeVar

from inguitive.session import (
    _get_data_registry,
)

_T = TypeVar("_T")

_LISTENERS_PREFIX = "__listeners__"

_state_name_registry: dict[str, State] = {}

# Context variable to track mutated state keys during request handling
_mutated_states: contextvars.ContextVar[set[str]] = contextvars.ContextVar(
    "mutated_states", default=set()
)


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


def _get_mutated_states() -> set[str]:
    """Return set of state keys mutated during current request.
    
    Returns:
        Copy of the set of state keys that were mutated via State.set()
        within the current _track_mutations() context.
    """
    return _mutated_states.get().copy()


def _get_state_by_name(name: str) -> State | None:
    """Look up a named State object from the global registry."""
    return _state_name_registry.get(name)


class State(Generic[_T]):
    """Reactive state container with per-session isolation.

    State values and listener sets are stored in the per-session data_registry,
    so each user's session maintains fully independent state. The State object
    itself is a module-level singleton used only as a handle — it holds no
    mutable runtime data after construction.

    Named states (State(value, "my_state")) are fully session-isolated.
    Unnamed states fall back to per-object storage, which is acceptable for
    states not shared across components via listen_to.
    """

    def __init__(self, initial_value: _T, name: str = ""):
        self._initial_value = initial_value
        self.name = name
        self._key = name if name else f"__anon_{uuid.uuid4().hex}"
        if name:
            _state_name_registry[name] = self

    def get(self) -> _T:
        """Return the current value for the active session."""
        return _get_data_registry().get(self._key, self._initial_value)

    def set(self, new_value: _T) -> None:
        """Write a new value into the active session's data registry."""
        _get_data_registry()[self._key] = new_value
        # Track mutation for auto-propagation in trigger handlers
        _mutated_states.get().add(self._key)

    @property
    def listeners(self) -> set[str]:
        """Return the set of component IDs listening to this state in the active session."""
        listeners_key = f"{_LISTENERS_PREFIX}{self._key}"
        data = _get_data_registry()
        if listeners_key not in data:
            data[listeners_key] = set()
        return data[listeners_key]

    def add_listener(self, component_id: str) -> None:
        """Register a component ID as a listener for the active session."""
        self.listeners.add(component_id)

    def remove_listener(self, component_id: str) -> None:
        """Remove a component ID from the listeners for the active session."""
        self.listeners.discard(component_id)
