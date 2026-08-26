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
    get_session_backend,
    get_session_id,
    push_update,
)

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

    The value is stored in the session's data_registry under the state's key
    ("counter_state"); push_update then re-renders only this session's
    counter-display component. The loop exits cleanly when the session is
    evicted (e.g. after the tab closes and the TTL elapses).
    """
    backend = get_session_backend()
    while True:
        await asyncio.sleep(1)
        session = await backend.get_session(session_id)
        if session is None:
            return  # session expired / tab gone — stop the loop

        session.data_registry["counter_state"] = (
            session.data_registry.get("counter_state", 0) + 1
        )
        session.mark_dirty()
        await backend.save_session(session)

        # Re-render only this user's counter component over their SSE stream.
        await push_update(session_id, "counter-display")


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Text(
            lambda: str(counter_state.get()),
            id="counter-display",
            listen_to="counter_state",
        ),
        Button("Start my counter", trigger="start_counter"),
        css="flex flex-col items-center gap-4 p-8 text-3xl",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.sse_app:app", host="0.0.0.0", port=8000, reload=True)
