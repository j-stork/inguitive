"""Tests for State mutation warnings."""

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
    # Don't call backend.save_session - just set the session in context
    # The middleware will handle persistence in real scenarios
    _set_current_session(session)
    yield
    _clear_current_session()


@pytest.fixture(autouse=True)
def reset_dev_mode():
    """Reset dev mode flag before and after each test."""
    # Ensure warnings are disabled before each test
    disable_dev_mode_warnings()

    yield

    # Ensure warnings are disabled after each test
    disable_dev_mode_warnings()


class TestStateWarnings:
    def test_warns_when_no_listeners(self, caplog):
        """Test that a warning is emitted when state is set with no listeners in dev mode."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")

        with caplog.at_level("WARNING"):
            state.set(1)

            assert len(caplog.records) == 1
            assert "test_state" in caplog.records[0].message
            assert "no component is listening" in caplog.records[0].message

    def test_no_warning_with_listeners(self, caplog):
        """Test that no warning is emitted when state has listeners."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")
        state.add_listener("comp-1")

        with caplog.at_level("WARNING"):
            state.set(1)

            # Filter for our specific logger
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

    def test_no_warning_in_production(self, caplog):
        """Test that no warning is emitted when dev mode is explicitly disabled."""
        # Explicitly ensure dev mode is off
        disable_dev_mode_warnings()

        state = State(0, "test_state")

        with caplog.at_level("WARNING"):
            state.set(1)

            # Filter for our specific logger
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

    def test_warning_for_anonymous_state(self, caplog):
        """Test that anonymous states also emit warnings."""
        enable_dev_mode_warnings()

        state = State(0)  # No name

        with caplog.at_level("WARNING"):
            state.set(1)

            assert len(caplog.records) == 1
            assert "no component is listening" in caplog.records[0].message

    def test_multiple_listeners_no_warning(self, caplog):
        """Test that multiple listeners also prevent warnings."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")
        state.add_listener("comp-1")
        state.add_listener("comp-2")
        state.add_listener("comp-3")

        with caplog.at_level("WARNING"):
            state.set(1)

            # Filter for our specific logger
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

    def test_warning_after_listener_removal(self, caplog):
        """Test that warning is emitted after all listeners are removed."""
        enable_dev_mode_warnings()

        state = State(0, "test_state")
        state.add_listener("comp-1")

        # First set should not warn
        with caplog.at_level("WARNING"):
            caplog.clear()
            state.set(1)
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

        # Remove listener
        state.remove_listener("comp-1")

        # Now it should warn
        with caplog.at_level("WARNING"):
            caplog.clear()
            state.set(2)
            assert len(caplog.records) == 1
            assert "test_state" in caplog.records[0].message
            assert "no component is listening" in caplog.records[0].message

    def test_disable_warnings(self, caplog):
        """Test that warnings can be disabled."""
        enable_dev_mode_warnings()
        disable_dev_mode_warnings()

        state = State(0, "test_state")

        with caplog.at_level("WARNING"):
            state.set(1)

            # Filter for our specific logger
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

    def test_toggle_warnings_on_off(self, caplog):
        """Test that warnings can be toggled on/off multiple times."""
        state = State(0, "test_state")

        # Start with warnings disabled (default from fixture)
        with caplog.at_level("WARNING"):
            caplog.clear()
            state.set(1)
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

        # Enable warnings
        enable_dev_mode_warnings()
        with caplog.at_level("WARNING"):
            caplog.clear()
            state.set(2)
            assert len(caplog.records) == 1

        # Disable warnings
        disable_dev_mode_warnings()
        with caplog.at_level("WARNING"):
            caplog.clear()
            state.set(3)
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

        # Enable again
        enable_dev_mode_warnings()
        with caplog.at_level("WARNING"):
            caplog.clear()
            state.set(4)
            assert len(caplog.records) == 1

    def test_create_app_dev_mode_false_disables_warnings(self, caplog):
        """Test that create_app(dev_mode=False) disables warnings."""
        from inguitive.fastapi import create_app

        # First create app with dev_mode=True (default)
        app1 = create_app(dev_mode=True)  # noqa: F841

        # Verify warnings are enabled
        state1 = State(0, "test_state_1")
        with caplog.at_level("WARNING"):
            caplog.clear()
            state1.set(1)
            assert len(caplog.records) == 1

        # Now create app with dev_mode=False
        app2 = create_app(dev_mode=False)  # noqa: F841

        # Verify warnings are disabled
        state2 = State(0, "test_state_2")
        with caplog.at_level("WARNING"):
            caplog.clear()
            state2.set(1)
            inguitive_warnings = [r for r in caplog.records if r.name == "inguitive.state"]
            assert len(inguitive_warnings) == 0

        # Clean up - re-enable warnings for other tests
        enable_dev_mode_warnings()
