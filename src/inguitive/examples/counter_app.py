"""
Reactive state + per-session isolation example using inguitive.

Run with: uvicorn inguitive.examples.counter_app:app --reload

Per-Session Counter
--------------------
This example demonstrates inguitive's core reactivity model: a ``State``
container whose ``set()`` triggers an HTMX out-of-band re-render of every
component that declared ``listen_to`` for that state name.

Two things are worth noting here:

1. **Per-session isolation.** ``State.get()`` and ``State.set()`` operate on
   the *current session's* value. Two browser windows (regular + incognito)
   each maintain their own independent counter — incrementing one never
   touches the other. The session id is shown so you can see the boundary.

2. **Dynamic attributes via callables.** The ``Text`` label's content and the
   ``Div``'s ``css`` are both zero-argument callables. inguitive calls them
   on every render, so the displayed count and its colour (red above 5) are
   derived from live state with no manual DOM code.

The handler returns ``update_components(*counter_state.listeners)`` — the
explicit-response form. See ``auto_propagation_app.py`` for the no-return
variant where the framework generates the OOB response for you.

To test:
1. Open this app in one regular browser window and one incognito/private window
2. Note the unique Session ID displayed in each window
3. Increment the counter in Window 1 — Window 2's counter stays unchanged
4. Both counters turn red once they exceed 5
"""

from inguitive import (
    Button,
    Div,
    Header,
    State,
    Text,
    create_app,
    get_session_id,
    update_components,
)

from .css import BASE_CONTAINER_CSS, BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS, HEADER_CSS

# --- App Setup ---
app = create_app()


# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
@app.trigger_handler
def increment():
    """Add 1 to the counter and re-render its listeners explicitly."""
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)


@app.trigger_handler
def reset():
    """Reset the counter to 0 and re-render its listeners explicitly."""
    counter_state.set(0)
    return update_components(*counter_state.listeners)


# --- Components ---
def Counter() -> Div:  # noqa: N802
    """Counter card. All dynamic values are callables re-evaluated on render."""

    def count_text() -> str:
        """Label text derived from the live counter value."""
        return f"Count: {counter_state.get()}"

    def count_css() -> str:
        """Red + bold once the count exceeds 5, otherwise neutral."""
        base = "text-xl text-center"
        if counter_state.get() > 5:
            return f"{base} text-red-400"
        return f"{base} text-white"

    return Div(
        Header(
            "Counter Example",
            css=HEADER_CSS,
        ),
        Text(
            count_text,
            css=count_css,
            listen_to="counter_state",
        ),
        Div(
            Button(
                "+1",
                trigger="increment",
                css=BUTTON_PRIMARY_CSS,
            ),
            Button(
                "Reset",
                trigger="reset",
                css=BUTTON_SECONDARY_CSS,
            ),
            css="grid grid-cols-2 gap-6 w-full max-w-md mx-auto",
        ),
        Text(
            f"Session ID: {get_session_id()}",
            css="text-center text-white/30",
        ),
        css=BASE_CONTAINER_CSS,
    )


# --- Routes ---
@app.page("/")
def home():
    return Counter()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.counter_app:app", host="0.0.0.0", port=8000, reload=True)
