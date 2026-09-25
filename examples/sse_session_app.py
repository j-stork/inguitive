"""
Session SSE counter example using inguitive.

Run with: uvicorn examples.sse_session_app:app --reload

A ``SessionState`` counter that increments every second as a per-session
background task. Each browser window starts its own loop via the button
and displays its own independent value, updating live via SSE.

The background task uses auto-propagation: ``SessionState.set()`` is
called from a task that inherited the handler's session context, so the
framework auto-pushes the update only to that session's SSE connections.
No explicit ``return update_components(...)`` is needed.

Clicking the button again after the loop finished resets the counter
to 0 and restarts it. Clicking while running is a no-op.
"""

import asyncio

from fastapi import FastAPI

from inguitive import UI, Button, Div, SessionState, Text, get_session_id, session_active

# --- App Setup ---
app = FastAPI()
ui = UI(app)

# --- State Instances ---
# SessionState: each session has its own isolated value.
counter_state = SessionState(0, "counter_state")

# Per-session registry of running counter loops. The live Task handle is
# not JSON-serializable, so it stays out of session state.
_counter_tasks: dict[str, asyncio.Task] = {}


# --- Trigger Handlers ---
@ui.trigger_handler
def start_counter():
    """Start the per-session counter loop, idempotently."""
    session_id = get_session_id()
    existing = _counter_tasks.get(session_id)
    if existing is not None and not existing.done():
        return  # already running — refuse the duplicate start
    counter_state.set(0)
    task = asyncio.create_task(_tick(session_id))
    _counter_tasks[session_id] = task
    task.add_done_callback(lambda t, sid=session_id: _counter_tasks.pop(sid, None))


# --- Background Task ---
async def _tick(session_id: str):
    """Increment the per-session counter once per second and auto-push via SSE.

    Runs in the trigger handler's copied context, so SessionState.set()
    writes to this session's isolated value and auto-pushes to this
    session's open SSE connections. The loop terminates when the counter
    reaches 10 or when session_active() returns False (all tabs closed).
    """
    while session_active():
        await asyncio.sleep(1)
        counter_state.set(counter_state.get() + 1)
        # Auto-propagation pushes to this session only. Explicit alternative:
        # return update_components(*counter_state.listeners)
        if counter_state.get() >= 10:
            return


# --- Routes ---
@app.get("/")
def home():
    return ui.page(
        Div(
            Text(
                lambda: str(counter_state.get()),
                css="text-6xl text-center font-mono",
                listen_to=counter_state,
            ),
            Button(
                "Start my counter",
                trigger=start_counter,
                css="px-3 py-2 bg-green-500",
            ),
            css="flex flex-col items-center gap-6 p-6",
        )
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.sse_session_app:app", host="0.0.0.0", port=8000, reload=True)
