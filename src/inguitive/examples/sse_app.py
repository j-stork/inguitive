"""
Server-Sent Events (SSE) example application using inguitive.

Run with: uvicorn inguitive.examples.sse_app:app --reload

Per-User Counter via push_update
---------------------------------
This example demonstrates inguitive's SSE server-push for a per-user counter
that increments by 1 every second. Unlike a global broadcast counter, each
browser session maintains its own independent count and receives updates only
on its own SSE stream.

The background task writes the incremented value directly into the session's
data_registry and then calls ``push_update(session_id, "counter-display")`` to
re-render just that user's component over their open SSE connection.

To test:
1. Open this app in one regular browser window and one incognito/private window
2. Click "Start my counter" in both windows
3. Each window's counter increments independently once per second
4. Closing one tab stops only that tab's loop when its session expires
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


# --- Trigger Handlers ---
@app.trigger_handler
def start_counter():
    """Start a background task that increments this session's counter."""
    session_id = get_session_id()
    asyncio.create_task(_tick(session_id))


# --- Background Task ---
async def _tick(session_id: str):
    """Increment the per-user counter once per second and push via SSE.

    session_context binds the session so State.set() writes to this user's
    isolated data and the session is persisted on exit. push_update is called
    inside the context with ``*counter_state.listeners`` — the same form used
    by ``update_components`` in a trigger handler — and reuses the in-memory
    session so it sees the just-set value without waiting for the save. The
    loop stops cleanly when the session no longer exists.
    """
    while True:
        await asyncio.sleep(1)
        async with session_context(session_id) as session:
            if session is None:
                return
            counter_state.set(counter_state.get() + 1)
            await push_update(session_id, *counter_state.listeners)


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
