"""Shared test fixtures for inguitive tests."""

import pytest

from inguitive.session import _clear_current_session
from inguitive.state import _global_state_values


@pytest.fixture(autouse=True)
def _clear_global_state():
    """Clear process-wide global state and session context before each test.

    State (global) stores values in _global_state_values, which persists
    across tests and causes cross-test pollution when multiple tests use
    the same state name. This fixture ensures each test starts with a clean
    global state and no leftover session binding from a previous test.
    """
    _global_state_values.clear()
    _clear_current_session()
    yield
    _global_state_values.clear()
    _clear_current_session()
