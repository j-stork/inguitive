"""
Trigger arguments example using inguitive.

Run with: uvicorn examples.trigger_args_app:app --reload

Demonstrates passing data from a component to its trigger handler via
``trigger_args`` and ``get_trigger_args()``, without a form. Four buttons
("+1", "+5", "+10", "-1") all point to the same ``add`` handler and differ
only in their ``trigger_args``. The handler reads the ``step`` value,
coerces it to ``int``, and adds it to the counter.

``trigger_args`` are serialised onto the HTMX POST URL as query
parameters (e.g. ``/_trigger/add?step=5``), so they are available even on
a plain ``Button`` with no enclosing ``Form``.

The handler uses auto-propagation: it calls ``State.set()`` and returns
nothing, so the framework re-renders the listeners automatically.
``return update_components(...)`` would be the explicit alternative.
"""

from fastapi import FastAPI

from inguitive import UI, Button, Div, State, Text, get_trigger_args

# --- App Setup ---
app = FastAPI()
ui = UI(app)

# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
@ui.trigger_handler
def add():
    """Add the ``step`` trigger_arg to the counter.

    ``step`` arrives as a string via ``get_trigger_args()`` because
    trigger args are serialised to query parameters, so it is coerced
    to ``int`` here. A missing or non-numeric value falls back to 0.
    """
    raw = get_trigger_args().get("step", 0)
    try:
        step = int(raw)
    except (TypeError, ValueError):
        step = 0
    counter_state.set(counter_state.get() + step)
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
                Button("+1", trigger=add, trigger_args={"step": 1}, css="px-3 py-2 bg-blue-500"),
                Button("+5", trigger=add, trigger_args={"step": 5}, css="px-3 py-2 bg-green-500"),
                Button("+10", trigger=add, trigger_args={"step": 10}, css="px-3 py-2 bg-yellow-500"),
                Button("-1", trigger=add, trigger_args={"step": -1}, css="px-3 py-2 bg-red-500"),
                css="flex gap-4 justify-center",
            ),
            css="flex flex-col items-center gap-6 p-6",
        )
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.trigger_args_app:app", host="0.0.0.0", port=8000, reload=True)
