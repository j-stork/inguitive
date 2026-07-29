"""Tests for State mutation warnings."""

import warnings

import pytest

from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _set_current_session,
    set_session_backend,
)
from inguitive.state import State, disable_dev_mode_warnings, enable_dev_mode_warnings


@pytest.fixture(autouse=True)
def cleanup_session():
    """Provide a clean session for each test."""
    backend = MemoryBackend()
    set_session_backend(backend)
    session = Session(session_id="test-session")
    backend.save_session(session)
    _set_current_session(session)
    yield
    _clear_current_session()


@pytest.fixture(autouse=True)
def reset_dev_mode():
    """Reset dev mode flag before and after each test."""
    # Save original state
    import inguitive.state as state_module

    original = state_module._dev_mode_warnings_enabled

    # Reset to False before test
    state_module._dev_mode_warnings_enabled = False

    yield

    # Restore original state
    state_module._dev_mode_warnings_enabled = original


class TestStateWarnings:
    def test_warns_when_no_listeners(self):
        """Test that a warning is emitted when state is set with no listeners in dev mode."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)

            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "test_state" in str(w[0].message)
            assert "no component is listening" in str(w[0].message)

    def test_no_warning_with_listeners(self):
        """Test that no warning is emitted when state has listeners."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")
        state.add_listener("comp-1")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)

            assert len(w) == 0

    def test_no_warning_in_production(self):
        """Test that no warning is emitted when dev mode is explicitly disabled."""
        # Explicitly ensure dev mode is off
        import inguitive.state as state_module

        state_module._dev_mode_warnings_enabled = False

        state = State(0, "test_state")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)

            assert len(w) == 0

    def test_warning_for_anonymous_state(self):
        """Test that anonymous states also emit warnings."""
        enable_dev_mode_warnings()

        state = State(0)  # No name

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)

            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "no component is listening" in str(w[0].message)

    def test_multiple_listeners_no_warning(self):
        """Test that multiple listeners also prevent warnings."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")
        state.add_listener("comp-1")
        state.add_listener("comp-2")
        state.add_listener("comp-3")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)

            assert len(w) == 0

    def test_warning_after_listener_removal(self):
        """Test that warning is emitted after all listeners are removed."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")
        state.add_listener("comp-1")

        # First set should not warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)
            assert len(w) == 0

        # Remove listener
        state.remove_listener("comp-1")

        # Now it should warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(2)
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "test_state" in str(w[0].message)
            assert "no component is listening" in str(w[0].message)

    def test_disable_warnings(self):
        """Test that warnings can be disabled."""
        enable_dev_mode_warnings()
        disable_dev_mode_warnings()

        state = State(0, "test_state")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)

            assert len(w) == 0

    def test_toggle_warnings_on_off(self):
        """Test that warnings can be toggled on/off multiple times."""
        state = State(0, "test_state")

        # Start with warnings disabled (default from fixture)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(1)
            assert len(w) == 0

        # Enable warnings
        enable_dev_mode_warnings()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(2)
            assert len(w) == 1

        # Disable warnings
        disable_dev_mode_warnings()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(3)
            assert len(w) == 0

        # Enable again
        enable_dev_mode_warnings()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state.set(4)
            assert len(w) == 1

    def test_create_app_dev_mode_false_disables_warnings(self):
        """Test that create_app(dev_mode=False) disables warnings."""
        from inguitive.fastapi import create_app

        # First create app with dev_mode=True (default)
        app1 = create_app(dev_mode=True)

        # Verify warnings are enabled
        state1 = State(0, "test_state_1")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state1.set(1)
            assert len(w) == 1

        # Now create app with dev_mode=False
        app2 = create_app(dev_mode=False)

        # Verify warnings are disabled
        state2 = State(0, "test_state_2")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            state2.set(1)
            assert len(w) == 0

        # Clean up - re-enable warnings for other tests
        enable_dev_mode_warnings()
