"""
Trigger arguments example using inguitive.

Run with: uvicorn inguitive.examples.trigger_args_app:app --reload

Passing Data via trigger_args
-----------------------------
This example demonstrates how to pass small pieces of data from a component
to its trigger handler **without a form**: the component declares
``trigger_args`` as a ``dict[str, str]``, and the handler reads them with
``get_trigger_args()``.

inguitive serialises ``trigger_args`` onto the HTMX POST URL as query
parameters (e.g. ``/_trigger/add?step=5``), so they are available even on a
plain ``Button`` with no enclosing ``Form``. Inside the handler,
``get_trigger_args()`` returns them as a plain ``dict[str, str]`` — the same
view regardless of whether the value came from ``trigger_args`` or a real
query string.

Here three buttons ("+1", "+5", "+10") all point to the same ``add`` handler
and differ only in their ``trigger_args``. The handler reads ``step``, coerces
it to ``int``, and adds it to the counter. This is the pattern to reach for
whenever the data is a fixed constant known at render time — a row id, a sort
column, a tab name.

Contrast with ``form_app.py``, where user-typed data flows through
``form_data`` instead, and with ``auto_propagation_app.py``, which shows the
no-return response style used here.

To test:
1. Click "+1", "+5", "+10" — the counter jumps by the matching amount
2. The displayed count updates immediately after each click
"""

from inguitive import Button, Div, State, Text, create_app, get_trigger_args, update_components

from .css import BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS

# --- App Setup ---
app = create_app()


# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
@app.trigger_handler
def add():
    """Add the ``step`` trigger_arg to the counter.

    ``step`` arrives as a string via ``get_trigger_args()`` because trigger
    args are serialised to query parameters, so it is coerced to ``int`` here.
    A missing or non-numeric value falls back to 0 rather than raising —
    trigger_args are attacker-controllable query params, never trust them
    blindly.
    """
    raw = get_trigger_args().get("step", "0")
    try:
        step = int(raw)
    except (TypeError, ValueError):
        step = 0
    counter_state.set(counter_state.get() + step)
    return update_components(*counter_state.listeners)


@app.trigger_handler
def reset():
    """Reset the counter to 0."""
    counter_state.set(0)
    return update_components(*counter_state.listeners)


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Text(
            lambda: f"Count: {counter_state.get()}",
            id="counter-label",
            css="text-xl text-center text-slate-900",
            listen_to="counter_state",
        ),
        Div(
            # All three buttons share one handler; only trigger_args differs.
            Button("+1", trigger="add", trigger_args={"step": "1"}, css=BUTTON_PRIMARY_CSS),
            Button("+5", trigger="add", trigger_args={"step": "5"}, css=BUTTON_PRIMARY_CSS),
            Button("+10", trigger="add", trigger_args={"step": "10"}, css=BUTTON_PRIMARY_CSS),
            css="flex gap-3 justify-center",
        ),
        Button(
            "Reset",
            trigger="reset",
            css=f"{BUTTON_SECONDARY_CSS} w-full",
        ),
        css="rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm mx-auto",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.trigger_args_app:app", host="0.0.0.0", port=8000, reload=True)
