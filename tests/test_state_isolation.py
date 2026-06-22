"""Tests for per-session state value and listener isolation."""

import pytest

from inguitive.session import (
    MemoryBackend,
    Session,
    clear_current_session,
    set_current_session,
    set_session_backend,
)
from inguitive.state import State, get_state_by_name


@pytest.fixture(autouse=True)
def isolated_sessions():
    """Set up a fresh MemoryBackend and two independent sessions for each test."""
    backend = MemoryBackend()
    set_session_backend(backend)

    session_a = Session(session_id="test-session-a")
    session_b = Session(session_id="test-session-b")
    backend.save_session(session_a)
    backend.save_session(session_b)

    yield session_a, session_b

    clear_current_session()


class TestStateValueIsolation:
    def test_independent_values_per_session(self, isolated_sessions):
        """Two sessions must maintain independent counter values."""
        session_a, session_b = isolated_sessions
        counter = State(0, "iso_counter")

        set_current_session(session_a)
        counter.set(5)

        set_current_session(session_b)
        counter.set(99)

        set_current_session(session_a)
        assert counter.get() == 5, "Session A value was overwritten by Session B"

        set_current_session(session_b)
        assert counter.get() == 99, "Session B value was overwritten by Session A"

    def test_initial_value_returned_before_first_set(self, isolated_sessions):
        """A session that has never called set() must receive the initial value."""
        session_a, session_b = isolated_sessions
        flag = State(False, "iso_flag")

        set_current_session(session_a)
        flag.set(True)

        set_current_session(session_b)
        assert flag.get() is False, "Uninitialised session must return initial_value"

    def test_string_state_isolation(self, isolated_sessions):
        """String state values must be isolated across sessions."""
        session_a, session_b = isolated_sessions
        theme = State("light", "iso_theme")

        set_current_session(session_a)
        theme.set("dark")

        set_current_session(session_b)
        assert theme.get() == "light"

        set_current_session(session_a)
        assert theme.get() == "dark"


class TestListenerIsolation:
    def test_listener_sets_are_independent(self, isolated_sessions):
        """Listeners added in one session must not appear in another."""
        session_a, session_b = isolated_sessions
        state = State(0, "iso_listeners")

        set_current_session(session_a)
        state.add_listener("comp-A1")
        state.add_listener("comp-A2")

        set_current_session(session_b)
        state.add_listener("comp-B1")

        set_current_session(session_a)
        assert "comp-A1" in state.listeners
        assert "comp-A2" in state.listeners
        assert "comp-B1" not in state.listeners, "Session B listener leaked into Session A"

        set_current_session(session_b)
        assert "comp-B1" in state.listeners
        assert "comp-A1" not in state.listeners, "Session A listener leaked into Session B"
        assert "comp-A2" not in state.listeners, "Session A listener leaked into Session B"

    def test_remove_listener_is_session_scoped(self, isolated_sessions):
        """Removing a listener in one session must not affect the other."""
        session_a, session_b = isolated_sessions
        state = State(0, "iso_remove")

        set_current_session(session_a)
        state.add_listener("shared-comp")

        set_current_session(session_b)
        state.add_listener("shared-comp")
        state.remove_listener("shared-comp")

        set_current_session(session_a)
        assert "shared-comp" in state.listeners, "Removing listener in Session B should not affect Session A"


class TestGlobalNameRegistry:
    def test_named_state_is_findable_by_name(self, isolated_sessions):
        """get_state_by_name must return the same object that was constructed."""
        state = State(42, "iso_named_lookup")
        assert get_state_by_name("iso_named_lookup") is state

    def test_unnamed_state_is_not_in_name_registry(self, isolated_sessions):
        """Unnamed states must not pollute the global name registry."""
        _ = State(0)
        assert get_state_by_name("") is None


class TestUnnamedStateBackwardCompat:
    def test_unnamed_state_get_set(self, isolated_sessions):
        """Unnamed states must still support basic get/set within a session."""
        session_a, _ = isolated_sessions
        set_current_session(session_a)

        state = State("hello")
        assert state.get() == "hello"
        state.set("world")
        assert state.get() == "world"
