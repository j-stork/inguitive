"""
Trigger arguments example using inguitive.

Run with: uvicorn examples.trigger_args_app:app --reload

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

Here four buttons ("+1", "+5", "+10", "-1") all point to the same ``add`` handler
and differ only in their ``trigger_args``. The handler reads ``step``, coerces
it to ``int``, and adds it to the counter — so a negative ``step`` subtracts.
This is the pattern to reach for whenever the data is a fixed constant known at
render time — a row id, a sort column, a tab name.

Contrast with ``form_app.py``, where user-typed data flows through
``form_data`` instead, and with ``auto_propagation_app.py``, which shows the
no-return response style used here.

To test:
1. Click "+1", "+5", "+10" — the counter jumps by the matching amount
2. Click "-1" — the counter decreases by 1
3. The displayed count updates immediately after each click
"""

from fastapi import FastAPI

from inguitive import (
    UI,
    Button,
    Div,
    State,
    Text,
    get_trigger_args,
    update_components,
)

from .css import (
    BUTTON_PRIMARY_BLUE_CSS,
    BUTTON_PRIMARY_GREEN_CSS,
    BUTTON_PRIMARY_RED_CSS,
    BUTTON_PRIMARY_YELLOW_CSS,
    BUTTON_SECONDARY_CSS,
    TEXT_CSS,
)
from .custom_components import BaseContainer, Card, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
@ui.trigger_handler
def add():
    """Add the ``step`` trigger_arg to the counter.

    ``step`` arrives as a string via ``get_trigger_args()`` because trigger
    args are serialised to query parameters, so it is coerced to ``int`` here.
    A missing or non-numeric value falls back to 0 rather than raising —
    trigger_args are attacker-controllable query params, never trust them
    blindly.
    """
    raw = get_trigger_args().get("step", 0)
    try:
        step = int(raw)
    except (TypeError, ValueError):
        step = 0
    counter_state.set(counter_state.get() + step)
    return update_components(*counter_state.listeners)


@ui.trigger_handler
def reset():
    """Reset the counter to 0."""
    counter_state.set(0)
    return update_components(*counter_state.listeners)


# --- Components ---
def AddButton(step: int, color: str) -> Button:  # noqa: N802
    """Reusable Button component to increment the counter by ``step``."""
    if color == "green":
        css = BUTTON_PRIMARY_GREEN_CSS
    elif color == "yellow":
        css = BUTTON_PRIMARY_YELLOW_CSS
    elif color == "red":
        css = BUTTON_PRIMARY_RED_CSS
    else:
        css = BUTTON_PRIMARY_BLUE_CSS

    return Button(
        f"+{step}" if step > 0 else f"{step}",
        trigger=add,
        trigger_args={"step": step},
        css=css,
    )


# --- Routes ---
@app.get("/")
def home():
    return ui.page(BaseContainer(
        InguitiveLogo(),
        Title("Trigger Args Example"),
        Card(
            Text(
                lambda: f"Count: {counter_state.get()}",
                css=f"{TEXT_CSS} text-xl text-center",
                listen_to=counter_state,
            ),
            Div(
                # All 4 buttons share one handler; only trigger_args differs.
                AddButton(step=1, color="blue"),
                AddButton(step=5, color="green"),
                AddButton(step=10, color="yellow"),
                AddButton(step=-1, color="red"),
                Button(
                    "Reset",
                    trigger=reset,
                    css=f"{BUTTON_SECONDARY_CSS}",
                ),
                css="grid grid-cols-5 gap-6 w-full",
            ),
        ),
    ))


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.trigger_args_app:app", host="0.0.0.0", port=8000, reload=True)
