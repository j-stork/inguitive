"""
Server-Sent Events (SSE) example application using inguitive.

Run with: uvicorn examples.sse_global_app:app --reload

Global Broadcast Counter
------------------------
This is the global-broadcast counterpart to ``sse_session_app.py``. A single
counter increments by 1 every second, with no limit, and every connected
browser tab sees the same value.

The difference from ``sse_session_app.py`` is where ``State.set()`` is called
from. Here the loop runs as a startup task with **no session bound**, so
``State.set()`` takes its background-task branch: the value is stored as a
global broadcast and the framework auto-pushes OOB HTML to every connected tab
whose components ``listen_to`` the state. No ``session_context``, no button,
and no idempotency guard are needed — the single startup task is the only
writer.

Contrast with ``sse_session_app.py``, where the loop is started from a trigger
handler with ``asyncio.create_task`` (inheriting the handler's bound session),
``SessionState.set()`` writes to one user's isolated data, and the framework
auto-pushes the update only to that session's open SSE connections.

To test:
1. Open this app in two browser windows (regular + incognito)
2. Both windows show the same counter, incrementing once per second in lockstep
3. Reload one window — it catches up to the current global value on reconnect
"""

import asyncio

from fastapi import FastAPI

from inguitive import Div, State, Text, UI

from .css import BRAND_COLORS
from .custom_components import BaseContainer, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Startup Task ---
@app.on_event("startup")
async def start_counter():
    """Start the single global counter loop when the server starts."""
    asyncio.create_task(_tick())


async def _tick():
    """Increment the global counter once per second and broadcast via SSE.

    Called from a startup task with no session bound, so ``State.set()`` writes
    to the global broadcast value and the framework auto-pushes OOB HTML to
    every connected tab whose components ``listen_to=counter_state``. Each
    session's ``Text`` component reads the global value as a fallback (it never
    sets the key locally), so all sessions display the same number.

    Runs forever; ``@app.on_event("startup")`` fires once per worker, so there
    is exactly one loop per worker process (see the multi-worker note in
    docs/guide/session-backends.md — use sticky sessions or a broker so all
    workers stay in sync).
    """
    while True:
        await asyncio.sleep(1)
        counter_state.set(counter_state.get() + 1)


# --- Components ---
def CounterDisplay() -> Div:  # noqa: N802
    """Display the global broadcast counter, updating live via SSE.

    The counter text and its color are derived from the live global
    ``counter_state`` value via callables re-evaluated on every render. The
    color cycles through the brand palette based on the value's divisibility
    (by 5, 4, 3, 2, in that order), defaulting to neutral text otherwise.
    """
    def dynamic_css() -> str:
        """Return a CSS class based on the current counter value."""
        value = counter_state.get()
        base_css = "text-6xl font-mono"
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
            Title("Global Broadcast Counter", level=2),
            Text(
                lambda: str(counter_state.get()),
                id="counter-display",
                listen_to=counter_state,
                css=dynamic_css,
            ),
        )

# --- Routes ---
@app.get("/")
def home():
    return ui.page(CounterDisplay())


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.sse_global_app:app", host="0.0.0.0", port=8000, reload=True)
