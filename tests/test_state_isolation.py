"""Tests for per-session state value and listener isolation."""

import pytest

from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _set_current_session,
    set_session_backend,
)
from inguitive.state import SessionState


@pytest.fixture(autouse=True)
def isolated_sessions():
    """Set up a fresh MemoryBackend and two independent sessions for each test."""
    backend = MemoryBackend()
    set_session_backend(backend)

    session_a = Session(session_id="test-session-a")
    session_b = Session(session_id="test-session-b")
    # Don't call backend.save_session - just set the sessions in context when needed
    # The tests will use _set_current_session to switch between them

    yield session_a, session_b

    _clear_current_session()


class TestStateValueIsolation:
    def test_independent_values_per_session(self, isolated_sessions):
        """Two sessions must maintain independent counter values."""
        session_a, session_b = isolated_sessions
        counter = SessionState(0, "iso_counter")

        _set_current_session(session_a)
        counter.set(5)

        _set_current_session(session_b)
        counter.set(99)

        _set_current_session(session_a)
        assert counter.get() == 5, "Session A value was overwritten by Session B"

        _set_current_session(session_b)
        assert counter.get() == 99, "Session B value was overwritten by Session A"

    def test_initial_value_returned_before_first_set(self, isolated_sessions):
        """A session that has never called set() must receive the initial value."""
        session_a, session_b = isolated_sessions
        flag = SessionState(False, "iso_flag")

        _set_current_session(session_a)
        flag.set(True)

        _set_current_session(session_b)
        assert flag.get() is False, "Uninitialised session must return initial_value"

    def test_string_state_isolation(self, isolated_sessions):
        """String state values must be isolated across sessions."""
        session_a, session_b = isolated_sessions
        theme = SessionState("light", "iso_theme")

        _set_current_session(session_a)
        theme.set("dark")

        _set_current_session(session_b)
        assert theme.get() == "light"

        _set_current_session(session_a)
        assert theme.get() == "dark"


class TestListenerIsolation:
    def test_listener_sets_are_independent(self, isolated_sessions):
        """Listeners added in one session must not appear in another."""
        session_a, session_b = isolated_sessions
        state = SessionState(0, "iso_listeners")

        _set_current_session(session_a)
        state.add_listener("comp-A1")
        state.add_listener("comp-A2")

        _set_current_session(session_b)
        state.add_listener("comp-B1")

        _set_current_session(session_a)
        assert "comp-A1" in state.listeners
        assert "comp-A2" in state.listeners
        assert "comp-B1" not in state.listeners, "Session B listener leaked into Session A"

        _set_current_session(session_b)
        assert "comp-B1" in state.listeners
        assert "comp-A1" not in state.listeners, "Session A listener leaked into Session B"
        assert "comp-A2" not in state.listeners, "Session A listener leaked into Session B"

    def test_remove_listener_is_session_scoped(self, isolated_sessions):
        """Removing a listener in one session must not affect the other."""
        session_a, session_b = isolated_sessions
        state = SessionState(0, "iso_remove")

        _set_current_session(session_a)
        state.add_listener("shared-comp")

        _set_current_session(session_b)
        state.add_listener("shared-comp")
        state.remove_listener("shared-comp")

        _set_current_session(session_a)
        assert "shared-comp" in state.listeners, (
            "Removing listener in Session B should not affect Session A"
        )


class TestNamedStateGetSet:
    def test_named_state_get_set(self, isolated_sessions):
        """Named states support basic get/set within a session."""
        session_a, _ = isolated_sessions
        _set_current_session(session_a)

        state = SessionState("hello", "greeting")
        assert state.get() == "hello"
        state.set("world")
        assert state.get() == "world"
