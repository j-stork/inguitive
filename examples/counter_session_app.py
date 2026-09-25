"""
Manual session counter example using inguitive.

Run with: uvicorn examples.counter_session_app:app --reload

A ``SessionState`` counter isolated per session. Each click of the "+1"
button increments it by 1. Open the app in two browser windows and each
shows its own independent value — ``SessionState`` is per-session.

The handler uses auto-propagation: it calls ``SessionState.set()`` and
returns nothing, so the framework detects which states changed and
re-renders their listeners automatically. ``return update_components(...)``
would be the explicit alternative.
"""

from fastapi import FastAPI

from inguitive import UI, Button, Div, SessionState, Text

# --- App Setup ---
app = FastAPI()
ui = UI(app)

# --- State Instances ---
# SessionState is per-session: each browser window has its own value.
counter_state = SessionState(0, "counter_state")


# --- Trigger Handlers ---
@ui.trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)
    # Auto-propagation re-renders the listeners. Explicit alternative:
    # return update_components(*counter_state.listeners)


@ui.trigger_handler
def reset():
    counter_state.set(0)
    # Auto-propagation re-renders the listeners. Explicit alternative:
    # return update_components(*counter_state.listeners)


# --- Routes ---
@app.get("/")
def home():
    return ui.page(
        Div(
            Text(
                lambda: f"Count: {counter_state.get()}",
                css="text-xl text-center",
                listen_to=counter_state,
            ),
            Div(
                Button("+1", trigger=increment, css="px-3 py-2 bg-blue-500"),
                Button("Reset", trigger=reset, css="px-3 py-2 bg-gray-400"),
                css="flex gap-6 justify-center",
            ),
            css="flex flex-col items-center gap-6 p-6",
        )
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.counter_session_app:app", host="0.0.0.0", port=8000, reload=True)
