"""Tests for session_context: binding a session outside an HTTP request."""

import pytest

from inguitive import State, session_context
from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _get_current_session_from_context,
    _set_current_session,
    get_session_backend,
    set_session_backend,
)

# Mark all test methods in this file as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def fresh_backend():
    """Use a fresh MemoryBackend and clear the current session for each test."""
    set_session_backend(MemoryBackend())
    _clear_current_session()
    yield
    _clear_current_session()


class TestSessionContext:
    """Tests for the session_context async context manager."""

    async def test_yields_session_when_it_exists(self, fresh_backend):
        session = Session(session_id="sid-1")
        await get_session_backend().save_session(session)

        async with session_context("sid-1") as s:
            assert s is not None
            assert s.session_id == "sid-1"

    async def test_yields_none_when_session_missing(self, fresh_backend):
        async with session_context("no-such-session") as s:
            assert s is None

    async def test_set_writes_to_session_isolated_data(self, fresh_backend):
        counter = State(0, "sc_counter")
        session = Session(session_id="sid-2")
        await get_session_backend().save_session(session)

        async with session_context("sid-2") as s:
            assert s is not None
            counter.set(5)
            assert counter.get() == 5

        # Value persisted to the backend after context exit
        loaded = await get_session_backend().get_session("sid-2")
        assert loaded.data_registry["sc_counter"] == 5

    async def test_set_outside_context_broadcasts_globally(self, fresh_backend):
        """State.set() with no active session must still hit the global path."""
        from inguitive.state import _global_state_values

        _global_state_values.clear()
        counter = State(0, "sc_global")

        counter.set(42)
        assert counter.get() == 42
        assert "sc_global" in _global_state_values

    async def test_context_does_not_leak_after_exit(self, fresh_backend):
        session = Session(session_id="sid-3")
        await get_session_backend().save_session(session)

        async with session_context("sid-3") as s:
            assert _get_current_session_from_context() is s
        assert _get_current_session_from_context() is None

    async def test_context_does_not_leak_on_missing_session(self, fresh_backend):
        async with session_context("missing"):
            pass
        assert _get_current_session_from_context() is None

    async def test_dirty_session_saved_on_exit(self, fresh_backend):
        counter = State(0, "sc_dirty")
        session = Session(session_id="sid-4")
        await get_session_backend().save_session(session)

        async with session_context("sid-4"):
            counter.set(7)

        loaded = await get_session_backend().get_session("sid-4")
        assert loaded.data_registry["sc_dirty"] == 7

    async def test_clean_session_not_re_saved(self, fresh_backend):
        """A session that is only read should not be marked dirty."""
        session = Session(session_id="sid-5")
        session.data_registry["preset"] = 1
        await get_session_backend().save_session(session)

        async with session_context("sid-5") as s:
            # Only read, no set()
            assert s.data_registry["preset"] == 1

        assert not s._dirty

    async def test_exception_in_body_still_clears_context(self, fresh_backend):
        session = Session(session_id="sid-6")
        await get_session_backend().save_session(session)

        with pytest.raises(ValueError):
            async with session_context("sid-6"):
                raise ValueError("boom")
        assert _get_current_session_from_context() is None

    async def test_exception_in_body_still_saves_dirty_session(self, fresh_backend):
        counter = State(0, "sc_exc")
        session = Session(session_id="sid-7")
        await get_session_backend().save_session(session)

        with pytest.raises(ValueError):
            async with session_context("sid-7"):
                counter.set(9)
                raise ValueError("boom")

        loaded = await get_session_backend().get_session("sid-7")
        assert loaded.data_registry["sc_exc"] == 9

    async def test_consecutive_contexts_are_independent(self, fresh_backend):
        counter = State(0, "sc_seq")
        s1 = Session(session_id="a")
        s2 = Session(session_id="b")
        await get_session_backend().save_session(s1)
        await get_session_backend().save_session(s2)

        async with session_context("a"):
            counter.set(11)

        async with session_context("b"):
            assert counter.get() == 0, "session b should not see a's value"
            counter.set(22)

        la = await get_session_backend().get_session("a")
        lb = await get_session_backend().get_session("b")
        assert la.data_registry["sc_seq"] == 11
        assert lb.data_registry["sc_seq"] == 22
