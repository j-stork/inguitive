"""
Server-Sent Events (SSE) example application using inguitive.

Run with: uvicorn inguitive.examples.sse_app:app --reload

Per-User Counter via push_update
---------------------------------
This example demonstrates inguitive's SSE server-push for a per-user counter
that increments by 1 every second until it reaches 10. Unlike a global
broadcast counter, each browser session maintains its own independent count
and receives updates only on its own SSE stream.

The background task runs inside a ``session_context`` so ``State.set()`` writes
to that user's isolated data, then calls ``push_update(session_id,
*counter_state.listeners)`` — the same form used by ``update_components`` in a
trigger handler — to re-render just that user's component over their open SSE
connection.

Starting the counter is idempotent: the guard reads the live ``asyncio.Task``
from a module-level dict (process memory, never serialized), so concurrent
clicks cannot spawn a second loop. This works on both MemoryBackend and
RedisBackend because the guard never touches serializable session state.
Clicking again after the loop finished resets the counter to 0 and restarts it.

To test:
1. Open this app in one regular browser window and one incognito/private window
2. Click "Start my counter" in both windows
3. Each window's counter increments independently once per second, to 10
4. Click again to restart; clicking while running is a no-op
5. Closing a tab stops only that tab's loop when its session is evicted
"""

import asyncio

from inguitive import (
    Button,
    Div,
    State,
    Text,
    create_app,
    get_session_id,
    push_update,
    session_context,
)

from .css import BUTTON_PRIMARY_CSS

# --- App Setup ---
app = create_app()


# --- State Instances ---
counter_state = State(0, "counter_state")

# Per-worker, in-process registry of running counter loops. The live Task
# handle is not JSON-serializable, so it stays out of the session's
# data_registry (which RedisBackend round-trips through to_dict/from_dict).
# Keyed by session_id so different sessions' loops never collide.
_counter_tasks: dict[str, asyncio.Task] = {}


# --- Trigger Handlers ---
@app.trigger_handler
def start_counter():
    """Start the per-user counter loop, idempotently.

    The guard reads the live Task from ``_counter_tasks`` — an atomic
    check-then-act with no ``await`` between the read and the store — so
    concurrent clicks cannot spawn a second loop. This holds regardless of
    session backend because the guard never reads serializable session state.

    If no loop is running, the counter is reset to 0 and a new loop starts.
    The handler must stay synchronous: if it ever becomes async and awaits
    between the check and the store, the atomicity is lost and an
    ``asyncio.Lock`` keyed by session_id would be needed around that section.
    """
    session_id = get_session_id()
    existing = _counter_tasks.get(session_id)
    if existing is not None and not existing.done():
        return  # already running — refuse the duplicate start
    counter_state.set(0)  # reset so the cap is restartable
    task = asyncio.create_task(_tick(session_id))
    _counter_tasks[session_id] = task
    task.add_done_callback(lambda t, sid=session_id: _counter_tasks.pop(sid, None))


# --- Background Task ---
async def _tick(session_id: str):
    """Increment the per-user counter once per second and push via SSE.

    ``session_context`` binds the session so ``State.set()`` writes to this
    user's isolated data and the session is persisted on exit.
    ``push_update`` is called inside the context with
    ``*counter_state.listeners`` and reuses the in-memory session so it sees
    the just-set value without waiting for the save. The loop stops at 10 or
    when the session no longer exists; ``add_done_callback`` in
    ``start_counter`` clears the module-level entry on either exit.
    """
    while True:
        await asyncio.sleep(1)
        async with session_context(session_id) as session:
            if session is None:
                return
            counter_state.set(counter_state.get() + 1)
            await push_update(session_id, *counter_state.listeners)
            if counter_state.get() >= 10:
                return


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Text(
            lambda: str(counter_state.get()),
            id="counter-display",
            listen_to="counter_state",
        ),
        Button(
            "Start my counter",
            trigger="start_counter",
            css=BUTTON_PRIMARY_CSS,
        ),
        css="flex flex-col justify-center items-center gap-6 p-6",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.sse_app:app", host="0.0.0.0", port=8000, reload=True)
