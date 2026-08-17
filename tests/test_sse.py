"""
Tests for SSE (Server-Sent Events) support.

Covers:
- Per-session SSE queue registry (including multi-tab, i.e. multiple queues per session)
- State.get() / State.set() outside a request context (global values)
- _push_sse_for_state: OOB HTML delivered to every queue for a session
- push_update: explicit per-session push fanned out to all open tabs
- GET /_sse route registration and response type
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from inguitive import State, create_app, push_update
from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _get_sse_queues,
    _register_sse_connection,
    _set_current_session,
    _sse_connections,
    _unregister_sse_connection,
    set_session_backend,
)
from inguitive.state import _global_state_values, _push_sse_for_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_registries():
    """Wipe SSE and global-state registries; reset to a fresh MemoryBackend."""
    _sse_connections.clear()
    _global_state_values.clear()
    set_session_backend(MemoryBackend())
    yield
    _sse_connections.clear()
    _global_state_values.clear()
    _clear_current_session()


@pytest.fixture
def app():
    return create_app(dev_mode=False)


# ---------------------------------------------------------------------------
# Queue registry — single session
# ---------------------------------------------------------------------------


def test_register_creates_queue():
    q = _register_sse_connection("sess-1")
    assert q in _get_sse_queues("sess-1")


def test_unregister_removes_specific_queue():
    q = _register_sse_connection("sess-2")
    _unregister_sse_connection("sess-2", q)
    assert q not in _get_sse_queues("sess-2")


def test_unregister_nonexistent_session_is_safe():
    # Must not raise even when the session was never registered.
    q: asyncio.Queue = asyncio.Queue()
    _unregister_sse_connection("does-not-exist", q)


def test_get_sse_queues_returns_empty_set_when_not_registered():
    assert _get_sse_queues("ghost") == set()


# ---------------------------------------------------------------------------
# Multi-tab: multiple queues per session
# ---------------------------------------------------------------------------


def test_two_tabs_same_session_each_get_own_queue():
    """Opening two tabs registers two independent queues for the same session."""
    q1 = _register_sse_connection("multi-sess")
    q2 = _register_sse_connection("multi-sess")
    queues = _get_sse_queues("multi-sess")
    assert q1 in queues
    assert q2 in queues
    assert q1 is not q2


def test_closing_first_tab_leaves_second_tab_intact():
    """Unregistering one queue must not affect the other open tab."""
    q1 = _register_sse_connection("tab-sess")
    q2 = _register_sse_connection("tab-sess")

    _unregister_sse_connection("tab-sess", q1)

    remaining = _get_sse_queues("tab-sess")
    assert q1 not in remaining
    assert q2 in remaining


def test_closing_second_tab_removes_session_entry():
    """When the last queue is removed the session entry disappears."""
    q1 = _register_sse_connection("last-tab")
    q2 = _register_sse_connection("last-tab")

    _unregister_sse_connection("last-tab", q1)
    _unregister_sse_connection("last-tab", q2)

    assert "last-tab" not in _sse_connections
    assert _get_sse_queues("last-tab") == set()


def test_multiple_sessions_are_independent():
    q1 = _register_sse_connection("a")
    q2 = _register_sse_connection("b")
    assert q1 in _get_sse_queues("a")
    assert q2 in _get_sse_queues("b")
    assert q1 not in _get_sse_queues("b")
    assert q2 not in _get_sse_queues("a")


# ---------------------------------------------------------------------------
# State.get() / State.set() without a session context
# ---------------------------------------------------------------------------


def test_state_get_returns_initial_when_no_session_and_no_global():
    s = State(42, "_sse_t1")
    assert s.get() == 42


def test_state_set_without_session_stores_global():
    s = State(0, "_sse_t2")
    s.set(99)
    assert _global_state_values[s._key] == 99


def test_state_get_returns_global_when_no_session():
    s = State(0, "_sse_t3")
    s.set(77)
    assert s.get() == 77


def test_state_get_session_value_takes_precedence_over_global():
    s = State(0, "_sse_t4")
    s.set(50)  # global (no session)

    session = Session(session_id="prec-sess")
    session.data_registry[s._key] = 200

    _set_current_session(session)
    try:
        assert s.get() == 200
    finally:
        _clear_current_session()


def test_state_get_falls_back_to_global_when_session_lacks_key():
    s = State(0, "_sse_t5")
    s.set(33)  # global (no session)

    session = Session(session_id="fallback-sess")
    _set_current_session(session)
    try:
        assert s.get() == 33
    finally:
        _clear_current_session()


def test_state_set_with_session_does_not_touch_global():
    s = State(0, "_sse_t6")
    session = Session(session_id="write-sess")
    _set_current_session(session)
    try:
        s.set(123)
    finally:
        _clear_current_session()
    assert s._key not in _global_state_values


# ---------------------------------------------------------------------------
# _push_sse_for_state — fan-out to all queues
# ---------------------------------------------------------------------------


def test_push_sse_sends_html_to_connected_queue():
    """HTML for a listening component reaches the SSE queue."""
    from inguitive import Text

    s = State("hello", "_sse_push_state")

    async def run():
        session = Session(session_id="push-sess")
        txt = Text(lambda: s.get(), id="push-txt", listen_to="_sse_push_state")
        session.component_registry["push-txt"] = txt
        session.data_registry["__listeners___sse_push_state"] = {"push-txt"}
        session.data_registry["_sse_push_state"] = "world"

        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q = _register_sse_connection("push-sess")
        await _push_sse_for_state("_sse_push_state")

        assert not q.empty()
        html = await q.get()
        assert "push-txt" in html
        assert "hx-swap-oob" in html

    asyncio.run(run())


def test_push_sse_fans_out_to_all_tabs_of_a_session():
    """All open tabs (queues) for a session receive the OOB HTML."""
    from inguitive import Text

    s = State("v", "_sse_multi_tab")

    async def run():
        session = Session(session_id="mt-sess")
        txt = Text(lambda: s.get(), id="mt-txt", listen_to="_sse_multi_tab")
        session.component_registry["mt-txt"] = txt
        session.data_registry["__listeners___sse_multi_tab"] = {"mt-txt"}
        session.data_registry["_sse_multi_tab"] = "updated"

        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        # Two tabs — two independent queues.
        q1 = _register_sse_connection("mt-sess")
        q2 = _register_sse_connection("mt-sess")

        await _push_sse_for_state("_sse_multi_tab")

        assert not q1.empty(), "Tab 1 should have received the push"
        assert not q2.empty(), "Tab 2 should have received the push"
        html1 = await q1.get()
        html2 = await q2.get()
        assert "mt-txt" in html1
        assert "mt-txt" in html2

    asyncio.run(run())


def test_push_sse_closed_tab_does_not_affect_remaining_tab():
    """After one tab disconnects, the remaining tab still receives pushes."""
    from inguitive import Text

    s = State("v", "_sse_closed_tab")

    async def run():
        session = Session(session_id="close-sess")
        txt = Text(lambda: s.get(), id="ct-txt", listen_to="_sse_closed_tab")
        session.component_registry["ct-txt"] = txt
        session.data_registry["__listeners___sse_closed_tab"] = {"ct-txt"}
        session.data_registry["_sse_closed_tab"] = "after-close"

        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q1 = _register_sse_connection("close-sess")
        q2 = _register_sse_connection("close-sess")

        # Close tab 1.
        _unregister_sse_connection("close-sess", q1)

        await _push_sse_for_state("_sse_closed_tab")

        # Tab 1 (closed) must receive nothing.
        assert q1.empty(), "Closed tab must not receive the push"
        # Tab 2 (open) must receive the push.
        assert not q2.empty(), "Open tab must still receive the push"

    asyncio.run(run())


def test_push_sse_skips_sessions_without_listeners():
    async def run():
        session = Session(session_id="no-listen-sess")
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q = _register_sse_connection("no-listen-sess")
        await _push_sse_for_state("_no_listen_state")
        assert q.empty()

    asyncio.run(run())


def test_push_sse_skips_disconnected_sessions():
    async def run():
        session = Session(session_id="disc-sess")
        session.data_registry["__listeners__disc_state"] = {"comp"}
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)
        # NOT in _sse_connections — must not raise.
        await _push_sse_for_state("disc_state")

    asyncio.run(run())


def test_push_sse_does_not_raise_on_render_error():
    """A session with missing component entries must not block other sessions."""
    async def run():
        session = Session(session_id="broken-sess")
        session.data_registry["__listeners__broken_state"] = {"missing-comp"}
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        _register_sse_connection("broken-sess")
        await _push_sse_for_state("broken_state")  # must not raise

    asyncio.run(run())


# ---------------------------------------------------------------------------
# push_update — fan-out to all queues
# ---------------------------------------------------------------------------


def test_push_update_sends_oob_html():
    from inguitive import Text

    s = State("initial", "_sse_pu_state")

    async def run():
        session = Session(session_id="pu-sess")
        txt = Text(lambda: s.get(), id="pu-txt")
        session.component_registry["pu-txt"] = txt
        session.data_registry["_sse_pu_state"] = "updated"
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q = _register_sse_connection("pu-sess")
        await push_update("pu-sess", "pu-txt")

        assert not q.empty()
        html = await q.get()
        assert "pu-txt" in html

    asyncio.run(run())


def test_push_update_fans_out_to_all_tabs():
    """push_update delivers OOB HTML to every open tab of the session."""
    from inguitive import Text

    s = State("v", "_sse_pu_multi")

    async def run():
        session = Session(session_id="pu-multi")
        txt = Text(lambda: s.get(), id="pu-m-txt")
        session.component_registry["pu-m-txt"] = txt
        session.data_registry["_sse_pu_multi"] = "value"
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q1 = _register_sse_connection("pu-multi")
        q2 = _register_sse_connection("pu-multi")
        await push_update("pu-multi", "pu-m-txt")

        assert not q1.empty(), "Tab 1 should receive the push"
        assert not q2.empty(), "Tab 2 should receive the push"

    asyncio.run(run())


def test_push_update_no_op_when_no_sse_connection():
    async def run():
        await push_update("no-sse-sess", "some-comp")

    asyncio.run(run())  # must not raise


def test_push_update_no_op_when_session_not_found():
    async def run():
        _register_sse_connection("ghost-sess")
        await push_update("ghost-sess", "comp-a")

    asyncio.run(run())  # must not raise


def test_push_update_multiple_components():
    from inguitive import Text

    s = State("v", "_sse_multi_comp")

    async def run():
        session = Session(session_id="mc-sess")
        for cid in ("mc-a", "mc-b"):
            session.component_registry[cid] = Text(lambda: s.get(), id=cid)
        session.data_registry["_sse_multi_comp"] = "value"
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q = _register_sse_connection("mc-sess")
        await push_update("mc-sess", "mc-a", "mc-b")

        assert not q.empty()
        html = await q.get()
        assert "mc-a" in html
        assert "mc-b" in html

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Backpressure — bounded queue, drop-oldest policy
# ---------------------------------------------------------------------------


def test_put_bounded_accepts_items_within_capacity():
    from inguitive.session import _put_bounded, _SSE_QUEUE_MAX

    q: asyncio.Queue = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    for i in range(_SSE_QUEUE_MAX):
        _put_bounded(q, f"update-{i}")
    assert q.qsize() == _SSE_QUEUE_MAX


def test_put_bounded_drops_oldest_when_full():
    from inguitive.session import _put_bounded, _SSE_QUEUE_MAX

    q: asyncio.Queue = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    for i in range(_SSE_QUEUE_MAX):
        _put_bounded(q, f"stale-{i}")

    # Queue is now at capacity; one more push should drop the oldest stale entry.
    _put_bounded(q, "fresh")

    assert q.qsize() == _SSE_QUEUE_MAX  # still bounded
    # Drain the queue and confirm the last item is the fresh one.
    items = []
    while not q.empty():
        items.append(q.get_nowait())
    assert items[-1] == "fresh"
    assert "stale-0" not in items, "Oldest stale entry should have been dropped"


def test_queue_stays_bounded_under_many_pushes():
    """Simulates a stalled consumer receiving many rapid pushes: queue must stay bounded."""
    from inguitive.session import _put_bounded, _SSE_QUEUE_MAX

    q: asyncio.Queue = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    # Push far more items than the queue can hold without consuming any.
    for i in range(_SSE_QUEUE_MAX * 10):
        _put_bounded(q, f"update-{i}")

    # Queue must never exceed capacity regardless of the burst.
    assert q.qsize() <= _SSE_QUEUE_MAX


def test_push_sse_stays_bounded_for_stalled_tab():
    """push_update to a non-consuming tab must not grow the queue beyond max."""
    from inguitive import Text
    from inguitive.session import _SSE_QUEUE_MAX

    s = State("v", "_sse_bp_state")

    async def run():
        session = Session(session_id="bp-sess")
        txt = Text(lambda: s.get(), id="bp-txt")
        session.component_registry["bp-txt"] = txt
        session.data_registry["_sse_bp_state"] = "value"
        from inguitive.session import get_session_backend
        await get_session_backend().save_session(session)

        q = _register_sse_connection("bp-sess")

        # Push far more than the queue can hold; the consumer never reads.
        for i in range(_SSE_QUEUE_MAX * 5):
            await push_update("bp-sess", "bp-txt")

        # Queue must be bounded.
        assert q.qsize() <= _SSE_QUEUE_MAX

    asyncio.run(run())


def test_cleanup_works_after_backpressure():
    """Unregistering a stalled (full) queue must still work correctly."""
    from inguitive.session import _put_bounded, _SSE_QUEUE_MAX

    q: asyncio.Queue = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    for i in range(_SSE_QUEUE_MAX * 3):
        _put_bounded(q, f"update-{i}")

    _register_sse_connection("bp-cleanup")
    # Replace the auto-created queue with the pre-filled one for this test.
    _sse_connections["bp-cleanup"] = {q}

    _unregister_sse_connection("bp-cleanup", q)

    # Session entry must be gone after unregistering the only queue.
    assert "bp-cleanup" not in _sse_connections


# ---------------------------------------------------------------------------
# GET /_sse route registration and response type
# ---------------------------------------------------------------------------


def test_sse_route_is_registered(app):
    """create_app must register a GET /_sse route."""
    paths = {route.path for route in app.routes}
    assert "/_sse" in paths


def test_sse_route_handler_returns_streaming_response(app):
    """The /_sse route must return a StreamingResponse with text/event-stream."""
    from unittest.mock import AsyncMock, MagicMock

    from fastapi.responses import StreamingResponse

    async def run():
        route_endpoint = None
        for route in app.routes:
            if getattr(route, "path", None) == "/_sse":
                route_endpoint = route.endpoint  # type: ignore[attr-defined]
                break
        assert route_endpoint is not None

        session = Session(session_id="hdr-sess")
        _set_current_session(session)
        try:
            mock_request = MagicMock()
            mock_request.is_disconnected = AsyncMock(return_value=True)
            response = await route_endpoint(mock_request)
        finally:
            _clear_current_session()

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

    asyncio.run(run())


def test_sse_disconnect_cleans_up_only_that_tab(app):
    """Disconnecting one SSE stream must leave other streams for the session intact."""
    from unittest.mock import AsyncMock, MagicMock

    # Track disconnect calls to control when the stream stops.
    call_count = 0

    async def run():
        nonlocal call_count

        # Register a second queue for the session before the route handler runs.
        session = Session(session_id="cleanup-sess")
        _set_current_session(session)

        # Pre-register a "second tab" queue.
        q_second = _register_sse_connection("cleanup-sess")

        route_endpoint = None
        for route in app.routes:
            if getattr(route, "path", None) == "/_sse":
                route_endpoint = route.endpoint  # type: ignore[attr-defined]
                break
        assert route_endpoint is not None

        # The mock disconnects immediately so the generator exits on the first iteration.
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=True)

        try:
            response = await route_endpoint(mock_request)
        finally:
            _clear_current_session()

        # Consume the generator to trigger cleanup.
        async for _ in response.body_iterator:
            break

        # The second tab's queue must still be registered.
        assert q_second in _get_sse_queues("cleanup-sess"), (
            "Closing one tab must not remove the other tab's queue"
        )

    asyncio.run(run())
