"""Tests for the global-vs-session SSE broadcast distinction.

``State.set()`` (global) broadcasts OOB HTML to every connected session's SSE
queues. ``SessionState.set()`` from a background task pushes only to the
current session's queues. This is the core global-vs-session SSE distinction
(Task 6.3).
"""

from __future__ import annotations

import asyncio

import pytest

from inguitive import SessionState, State
from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _get_sse_queues,
    _register_sse_connection,
    _set_current_session,
    _sse_connections,
    set_session_backend,
)
from inguitive.state import (
    _global_state_values,
    _push_sse_for_session_state,
    _push_sse_for_state,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Wipe registries and reset backend before each test."""
    _sse_connections.clear()
    _global_state_values.clear()
    set_session_backend(MemoryBackend())
    _clear_current_session()
    yield
    _sse_connections.clear()
    _global_state_values.clear()
    _clear_current_session()


# ---------------------------------------------------------------------------
# State.set() (global) — broadcast to all sessions
# ---------------------------------------------------------------------------


def test_global_state_set_broadcasts_to_all_sessions():
    """State.set() from a background task pushes to every connected session."""
    from inguitive import Text

    s = State("initial", "broadcast_state")

    async def run():
        # Two sessions, each with a listener for the state and an SSE queue.
        for sid in ("sess-a", "sess-b"):
            session = Session(session_id=sid)
            _set_current_session(session)
            txt = Text(lambda: s.get(), id=f"txt-{sid}", listen_to=s)
            session.component_registry[f"txt-{sid}"] = txt
            session.data_registry[f"__listeners__broadcast_state"] = {f"txt-{sid}"}
            from inguitive.session import get_session_backend
            await get_session_backend().save_session(session)
            _register_sse_connection(sid)
        _clear_current_session()

        # Mutate from a background-task context (no session bound).
        s.set("updated")

        # Let the scheduled task run.
        await asyncio.sleep(0.05)

        for sid in ("sess-a", "sess-b"):
            queues = _get_sse_queues(sid)
            assert len(queues) == 1
            q = next(iter(queues))
            assert not q.empty(), f"Session {sid} should have received the broadcast"
            html = await q.get()
            assert f"txt-{sid}" in html
            assert "hx-swap-oob" in html

    asyncio.run(run())


def test_global_state_set_broadcast_skips_sessions_without_listeners():
    """Sessions without listeners for the state do not receive a push."""

    async def run():
        # Session with a listener.
        from inguitive import Text

        s = State("v", "has_listener_state")
        session1 = Session(session_id="with-listener")
        _set_current_session(session1)
        txt = Text(lambda: s.get(), id="wl-txt", listen_to=s)
        session1.component_registry["wl-txt"] = txt
        session1.data_registry["__listeners__has_listener_state"] = {"wl-txt"}
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session1)
        _register_sse_connection("with-listener")

        # Session without a listener for this state.
        session2 = Session(session_id="no-listener")
        await get_session_backend().save_session(session2)
        _register_sse_connection("no-listener")
        _clear_current_session()

        s.set("updated")
        await asyncio.sleep(0.05)

        wl_queues = _get_sse_queues("with-listener")
        assert not next(iter(wl_queues)).empty()

        nl_queues = _get_sse_queues("no-listener")
        assert next(iter(nl_queues)).empty(), "Session without listeners should not receive a push"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# SessionState.set() — push to current session only
# ---------------------------------------------------------------------------


def test_session_state_set_pushes_to_current_session_only():
    """SessionState.set() from a background task pushes to the bound session only."""
    from inguitive import Text

    s = SessionState(0, "session_only_state")

    async def run():
        # Two sessions, both with listeners and SSE queues.
        for sid in ("mine", "theirs"):
            session = Session(session_id=sid)
            _set_current_session(session)
            txt = Text(lambda: s.get(), id=f"txt-{sid}", listen_to=s)
            session.component_registry[f"txt-{sid}"] = txt
            session.data_registry[f"__listeners__session_only_state"] = {f"txt-{sid}"}
            session.data_registry["session_only_state"] = 0
            from inguitive.session import get_session_backend
            await get_session_backend().save_session(session)
            _register_sse_connection(sid)

        # Bind "mine" as the current session (simulating a background task
        # that inherited the contextvars from the trigger handler).
        mine_session = Session(session_id="mine")
        _set_current_session(mine_session)

        # Mutate — should push to "mine" only, not "theirs".
        s.set(42)
        await asyncio.sleep(0.05)

        mine_queues = _get_sse_queues("mine")
        assert not next(iter(mine_queues)).empty(), "Current session should receive the push"
        html = await next(iter(mine_queues)).get()
        assert "txt-mine" in html

        theirs_queues = _get_sse_queues("theirs")
        assert next(iter(theirs_queues)).empty(), "Other session should NOT receive the push"

    asyncio.run(run())


def test_session_state_set_no_session_falls_back_to_broadcast():
    """SessionState.set() with no session bound stores globally and broadcasts."""

    async def run():
        from inguitive import Text

        s = SessionState("v", "no_session_state")
        session = Session(session_id="ns-sess")
        _set_current_session(session)
        txt = Text(lambda: s.get(), id="ns-txt", listen_to=s)
        session.component_registry["ns-txt"] = txt
        session.data_registry["__listeners__no_session_state"] = {"ns-txt"}
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)
        _register_sse_connection("ns-sess")
        _clear_current_session()

        # No session bound — falls back to global store + broadcast.
        s.set("global-value")
        await asyncio.sleep(0.05)

        assert _global_state_values["no_session_state"] == "global-value"
        q = next(iter(_get_sse_queues("ns-sess")))
        assert not q.empty()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Direct helper tests (no event loop scheduling)
# ---------------------------------------------------------------------------


def test_push_sse_for_state_broadcasts_to_all():
    """_push_sse_for_state fans out to every session with listeners."""
    from inguitive import Text

    s = State("v", "direct_broadcast")

    async def run():
        for sid in ("d-a", "d-b"):
            session = Session(session_id=sid)
            _set_current_session(session)
            txt = Text(lambda: s.get(), id=f"d-txt-{sid}", listen_to=s)
            session.component_registry[f"d-txt-{sid}"] = txt
            session.data_registry["__listeners__direct_broadcast"] = {f"d-txt-{sid}"}
            from inguitive.session import get_session_backend
            await get_session_backend().save_session(session)
            _register_sse_connection(sid)
        _clear_current_session()

        await _push_sse_for_state("direct_broadcast")

        for sid in ("d-a", "d-b"):
            q = next(iter(_get_sse_queues(sid)))
            assert not q.empty()
            html = await q.get()
            assert f"d-txt-{sid}" in html

    asyncio.run(run())


def test_push_sse_for_session_state_targets_one_session():
    """_push_sse_for_session_state pushes to only the specified session."""
    from inguitive import Text

    s = State("v", "direct_single")

    async def run():
        for sid in ("target", "bystander"):
            session = Session(session_id=sid)
            _set_current_session(session)
            txt = Text(lambda: s.get(), id=f"s-txt-{sid}", listen_to=s)
            session.component_registry[f"s-txt-{sid}"] = txt
            session.data_registry["__listeners__direct_single"] = {f"s-txt-{sid}"}
            from inguitive.session import get_session_backend
            await get_session_backend().save_session(session)
            _register_sse_connection(sid)
        _clear_current_session()

        await _push_sse_for_session_state("direct_single", "target")

        target_q = next(iter(_get_sse_queues("target")))
        assert not target_q.empty()
        html = await target_q.get()
        assert "s-txt-target" in html

        bystander_q = next(iter(_get_sse_queues("bystander")))
        assert bystander_q.empty(), "Bystander session should not receive the push"

    asyncio.run(run())
