"""
TemplateComponent example using inguitive.

Run with: uvicorn inguitive.examples.template_app:app --reload

Rendering a Jinja2 Template as a Component
------------------------------------------
This example demonstrates ``TemplateComponent``, which renders a Jinja2
template string as an inguitive component — useful when a piece of markup
is easier to express as a template than by composing ``Div``/``Text``/etc.

Two things are worth noting:

1. **Context values can be callables.** Any keyword argument passed to
   ``TemplateComponent`` becomes a template variable. If the value is a
   zero-argument callable, it is resolved on every render, so a live
   ``State`` value can flow in via ``value=counter_state.get``. Combined
   with ``listen_to``, the template re-renders whenever the state changes.

2. **Autoescaping is on.** The Jinja2 environment uses
   ``select_autoescape(["html", "xml"])``, so values interpolated via
   ``{{ ... }}`` are HTML-escaped automatically — the same safety as the
   built-in components.

The template here is an inline string (no external file needed) that
renders a styled counter card. The card is wrapped in a regular ``Div``
with ``Button`` components for the controls, so only the card itself uses
``TemplateComponent``. The handlers use auto-propagation (see
``auto_propagation_app.py``), so no explicit return is needed.

``TemplateComponent.from_file(path, **context)`` is the file-based
alternative when a template is large or shared across pages.

To test:
1. The page shows a counter card rendered from the Jinja2 template
2. Click "+1" — the template re-renders with the new value
3. Click "Reset" — the template re-renders with 0
"""

from inguitive import Button, Div, Header, State, TemplateComponent, create_app

from .css import (
    BASE_CONTAINER_CSS,
    BUTTON_PRIMARY_CSS,
    BUTTON_SECONDARY_CSS,
    HEADER_CSS,
)

# --- App Setup ---
app = create_app()


# --- State Instances ---
# A simple counter, same mechanism as counter_app.py but rendered via a
# Jinja2 template instead of Div/Text components.
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
@app.trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)


@app.trigger_handler
def reset():
    counter_state.set(0)


# --- Components ---
# An inline Jinja2 template rendered as a component. The {{ value }} variable
# is fed from the ``value=counter_state.get`` callable (resolved on every
# render), so the template reflects the live state. Autoescaping applies to
# the interpolated value.
COUNTER_TEMPLATE = """
<div class="w-sm p-6 space-y-6 rounded-xl bg-gray-100 shadow-lg">
  <p class="text-xl text-center">Count: {{ value }}</p>
  <p class="text-center text-gray-500">Rendered via TemplateComponent</p>
</div>
"""


def CounterCard() -> TemplateComponent:  # noqa: N802
    return TemplateComponent(
        COUNTER_TEMPLATE,
        value=lambda: counter_state.get(),  # callable → resolved on each render
        listen_to="counter_state",  # re-render when the state changes
    )


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Header("TemplateComponent Example", css=HEADER_CSS),
        CounterCard(),
        Div(
            Button(
                "+1",
                trigger="increment",
                css=f"{BUTTON_PRIMARY_CSS} w-full"
            ),
            Button(
                "Reset",
                trigger="reset",
                css=f"{BUTTON_SECONDARY_CSS} w-full"
            ),
            css="flex w-sm gap-6",
        ),
        css=BASE_CONTAINER_CSS,
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.template_app:app", host="0.0.0.0", port=8000, reload=True)
