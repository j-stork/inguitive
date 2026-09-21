"""Tests for the ``session_active()`` predicate.

``session_active()`` returns True when the current session (resolved via
contextvars) has at least one open SSE connection, and False otherwise. It is
the explicit termination condition for session-scoped background tasks.
"""

import pytest

from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _register_sse_connection,
    _set_current_session,
    _unregister_sse_connection,
    session_active,
    set_session_backend,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Fresh backend + no session bound before each test."""
    set_session_backend(MemoryBackend())
    _clear_current_session()
    yield
    _clear_current_session()


class TestSessionActive:
    def test_false_when_no_session_bound(self):
        """No session in context -> False, regardless of SSE connections."""
        _register_sse_connection("orphan-sess")
        assert session_active() is False

    def test_false_when_session_has_no_sse_connections(self):
        """Session is bound but has zero open SSE queues -> False."""
        session = Session(session_id="lonely-sess")
        _set_current_session(session)
        assert session_active() is False

    def test_true_when_session_has_open_sse_connection(self):
        """Session is bound and has at least one SSE queue -> True."""
        session = Session(session_id="connected-sess")
        _set_current_session(session)
        _register_sse_connection("connected-sess")
        assert session_active() is True

    def test_true_with_multiple_connections_for_same_session(self):
        """Multiple open tabs (queues) for the session -> True."""
        session = Session(session_id="multi-sess")
        _set_current_session(session)
        _register_sse_connection("multi-sess")
        _register_sse_connection("multi-sess")
        assert session_active() is True

    def test_false_after_last_connection_closes(self):
        """When the last SSE queue is unregistered, session_active() flips to False."""
        session = Session(session_id="closing-sess")
        _set_current_session(session)
        q = _register_sse_connection("closing-sess")
        assert session_active() is True

        _unregister_sse_connection("closing-sess", q)
        assert session_active() is False

    def test_false_after_session_cleared(self):
        """Even with an open SSE queue, clearing the session context -> False."""
        session = Session(session_id="cleared-sess")
        _set_current_session(session)
        _register_sse_connection("cleared-sess")
        assert session_active() is True

        _clear_current_session()
        assert session_active() is False

    def test_checks_only_the_current_session(self):
        """Connections for a *different* session do not make session_active() True."""
        session = Session(session_id="this-sess")
        _set_current_session(session)
        # Register connections for a different session, not the bound one.
        _register_sse_connection("other-sess")
        assert session_active() is False

        # Now register a connection for the bound session -> True.
        _register_sse_connection("this-sess")
        assert session_active() is True
