"""
Server-Sent Events (SSE) example application using inguitive.

Run with: uvicorn inguitive.examples.sse_session_app:app --reload

Per-User Counter via SessionState
---------------------------------
This example demonstrates inguitive's session-scoped SSE push for a per-user
counter that increments by 1 every second until it reaches 10. Unlike the
global broadcast counter in ``sse_global_app.py``, each browser session
maintains its own independent count and receives updates only on its own SSE
stream.

The loop is started from a trigger handler with ``asyncio.create_task``. The
task inherits the handler's bound session via Python's contextvar copy
semantics, so:

- ``SessionState.set()`` writes to *this* session's isolated data and the
  framework auto-pushes the OOB update to this session's open SSE connections.
- ``session_active()`` returns ``True`` while at least one tab for this
  session has an open SSE connection, and ``False`` once they all close —
  the loop's ``while session_active():`` terminates the task cleanly.

No ``session_context`` and no ``push_update`` are needed: the auto-push
path covers the entire workflow. This matches the vision code in TODO.md.

Starting the counter is idempotent: the guard reads the live ``asyncio.Task``
from a module-level dict (process memory, never serialized), so concurrent
clicks cannot spawn a second loop. Clicking again after the loop finished
resets the counter to 0 and restarts it.

To test:
1. Open this app in one regular browser window and one incognito/private window
2. Click "Start my counter" in both windows
3. Each window's counter increments independently once per second, to 10
4. Click again to restart; clicking while running is a no-op
5. Closing all of a session's tabs stops that session's loop via
   ``session_active()`` returning ``False``
"""

import asyncio

from fastapi import FastAPI

from inguitive import (
    Button,
    Div,
    SessionState,
    Text,
    UI,
    get_session_id,
    session_active,
)

from .css import BRAND_COLORS, BUTTON_PRIMARY_GREEN_CSS
from .custom_components import BaseContainer, Card, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- State Instances ---
# SessionState: each session has its own isolated value. Auto-push targets
# only the session whose context the .set() call runs in.
counter_state = SessionState(0, "counter_state")

# Per-worker, in-process registry of running counter loops. The live Task
# handle is not JSON-serializable, so it stays out of the session's
# data_registry (which RedisBackend round-trips through to_dict/from_dict).
# Keyed by session_id so different sessions' loops never collide.
_counter_tasks: dict[str, asyncio.Task] = {}


# --- Trigger Handlers ---
@ui.trigger_handler
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

    ``asyncio.create_task`` copies the current context (including the bound
    session) into the new task, so ``session_active()`` and
    ``SessionState.set()`` inside ``_tick`` resolve to *this* session without
    any explicit ``session_context`` binding.
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
    """Increment the per-user counter once per second and auto-push via SSE.

    Runs in the trigger handler's copied context, so ``counter_state`` (a
    ``SessionState``) reads and writes this session's isolated value, and
    each ``.set()`` triggers the framework's auto-push to this session's
    open SSE connections. No explicit ``push_update`` call is needed.

    The loop terminates when either:
    - the counter reaches 10 (the cap), or
    - ``session_active()`` returns ``False`` (all of this session's SSE
      connections have closed — e.g. the user closed every tab).
    ``add_done_callback`` in ``start_counter`` clears the module-level entry
    on either exit.
    """
    while session_active():
        await asyncio.sleep(1)
        counter_state.set(counter_state.get() + 1)
        if counter_state.get() >= 10:
            return


# --- Components ---
def CounterDisplay() -> Div:  # noqa: N802
    """Display the per-user counter, updating live via SSE.

    The counter text and its color are derived from the live per-session
    ``counter_state`` value via callables re-evaluated on every render. The
    color cycles through the brand palette based on the value's divisibility
    (by 5, 4, 3, 2, in that order), defaulting to neutral text otherwise.
    A button starts (or restarts) the per-user counter loop.
    """
    def dynamic_css() -> str:
        """Return a CSS class based on the current counter value."""
        value = counter_state.get()
        base_css = "text-6xl font-mono text-center"
        if value % 5 == 0:
            return f"{base_css} text-{BRAND_COLORS['blue']}"
        elif value % 4 == 0:
            return f"{base_css} text-{BRAND_COLORS['green']}"
        elif value % 3 == 0:
            return f"{base_css} text-{BRAND_COLORS['yellow']}"
        elif value % 2 == 0:
            return f"{base_css} text-{BRAND_COLORS['red']}"
        return f"{base_css} text-{BRAND_COLORS['text_0']}"

    return BaseContainer(
        InguitiveLogo(),
        Title("SSE Events Example"),
        Title("Per-User Counter via SessionState", level=2),
        Card(
            Text(
                lambda: str(counter_state.get()),
                id="counter-display",
                listen_to=counter_state,
                css=dynamic_css,
            ),
            Button(
                "Start my counter",
                trigger=start_counter,
                css=f"w-full {BUTTON_PRIMARY_GREEN_CSS}",
            ),
        ),
    )


# --- Routes ---
@app.get("/")
def home():
    return ui.page(CounterDisplay())


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.sse_session_app:app", host="0.0.0.0", port=8000, reload=True)
