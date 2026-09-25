"""
Global SSE counter example using inguitive.

Run with: uvicorn examples.sse_global_app:app --reload

A ``State`` counter that automatically increments every second as a
background task when the server starts. Since the counter is global,
all sessions (browser windows) display the same value, updating live
via SSE.

The background task uses auto-propagation: ``State.set()`` is called
with no session bound, so the framework broadcasts the update to every
connected tab whose components ``listen_to`` the state. No explicit
``return update_components(...)`` is needed.
"""

import asyncio

from fastapi import FastAPI

from inguitive import UI, Div, State, Text

# --- App Setup ---
app = FastAPI()
ui = UI(app)

# --- State Instances ---
# State is global: the same value is shared across all sessions.
counter_state = State(0, "counter_state")


# --- Startup Task ---
@app.on_event("startup")
async def start_counter():
    """Start the global counter loop when the server starts."""
    asyncio.create_task(_tick())


async def _tick():
    """Increment the global counter once per second and broadcast via SSE.

    Runs with no session bound, so State.set() writes to the global
    broadcast value and the framework auto-pushes OOB HTML to every
    connected tab whose components listen_to=counter_state.
    """
    while True:
        await asyncio.sleep(1)
        counter_state.set(counter_state.get() + 1)
        # Auto-propagation broadcasts to all sessions. Explicit alternative:
        # return update_components(*counter_state.listeners)


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
            css="flex flex-col items-center gap-6 p-6",
        )
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.sse_global_app:app", host="0.0.0.0", port=8000, reload=True)
