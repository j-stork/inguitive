"""
Auto-propagation example using inguitive.

Run with: uvicorn inguitive.examples.auto_propagation_app:app --reload

Letting the Framework Build the Response
-----------------------------------------
This example demonstrates inguitive's **auto-propagation**: when a trigger
handler mutates state and returns nothing (or an empty string), the framework
detects which ``State`` objects changed during the handler's execution and
automatically builds the out-of-band HTMX response for every component
listening to them.

The ``increment`` and ``reset`` handlers here simply call ``counter_state.set``
and **return nothing** — no ``return update_components(...)``. Compare them
with the handlers in ``counter_app.py`` and ``trigger_args_app.py``, which
build the response explicitly. The two are equivalent for a single state;
auto-propagation shines when several states change in one handler and you do
not want to enumerate their listeners by hand.

Mechanism: each ``State.set()`` call records the state name; after the handler
returns, if there is no explicit non-empty response, the framework collects
the union of listeners across every mutated state and renders exactly those
components as OOB swaps. An explicit non-empty return (e.g.
``return update_components(...)``) overrides this, which is why that form in
the other examples takes precedence.

To test:
1. Click "+1" repeatedly — the count updates each time, with no return in the handler
2. Click "Reset" — the count returns to 0
"""

from inguitive import Button, Div, Header, State, Text, create_app

from .css import BASE_CONTAINER_CSS, BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS, HEADER_CSS

# --- App Setup ---
app = create_app()


# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
# Note: neither handler returns anything. State.set() alone is enough — the
# framework inspects which states were mutated and renders their listeners.
@app.trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)


@app.trigger_handler
def reset():
    counter_state.set(0)


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Header(
            "Auto-Propagation Example",
            css=HEADER_CSS,
        ),
        Text(
            lambda: f"Count: {counter_state.get()}",
            css="text-xl text-center text-white",
            listen_to="counter_state",
        ),
        Div(
            Button("+1", trigger="increment", css=BUTTON_PRIMARY_CSS),
            Button("Reset", trigger="reset", css=BUTTON_SECONDARY_CSS),
            css="grid grid-cols-2 gap-6 w-full max-w-md mx-auto",
        ),
        css=BASE_CONTAINER_CSS,
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.auto_propagation_app:app", host="0.0.0.0", port=8000, reload=True)
