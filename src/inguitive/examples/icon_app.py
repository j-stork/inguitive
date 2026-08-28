"""
Icon example using inguitive.

Run with: uvicorn inguitive.examples.icon_app:app --reload

The Icon Component
-----------------
This example demonstrates the ``Icon`` component, which renders raw SVG markup
inside the page. Two things are worth noting:

1. **Markup-safe SVG.** ``Icon`` accepts a ``str`` or, as here, a
   ``markupsafe.Markup`` instance. Wrapping the SVG in ``Markup`` tells the
   framework's escaping that the string is already safe, so the SVG tags are
   emitted verbatim rather than entity-escaped. The framework also rewrites
   the SVG's ``class`` attribute to apply the ``css`` you pass in. See
   ``svg.py`` for the source of the two icons used here.

2. **Dynamic icon via a callable.** ``Icon``'s first argument can be a
   zero-argument callable returning the SVG string, re-evaluated on every
   render. Here it switches between ``MOON`` and ``SUN`` based on
   ``mode_state``, so a single ``Icon`` component swaps its glyph when the
   state changes.

3. Also note that an ``Icon`` component can easily be used as a button label.

The button toggles ``mode_state``; the icon re-renders via auto-propagation
(see ``auto_propagation_app.py``). Contrast with ``counter_app.py``, where
dynamic attributes are shown on ``Text`` and ``Div`` rather than on ``Icon``.

To test:
1. The page shows a moon icon and a "Toggle" button
2. Click the button — the icon swaps to a sun
3. Click again — it swaps back to a moon
"""

from inguitive import Button, Div, Header, Icon, State, create_app

from .css import BASE_CONTAINER_CSS, BUTTON_PRIMARY_CSS, HEADER_CSS
from .svg import ARROWS_UP_DOWN, MOON, SUN

# --- App Setup ---
app = create_app()


# --- State Instances ---
# "moon" or "sun" — controls which SVG the Icon renders.
mode_state = State("moon", "mode_state")


# --- Trigger Handlers ---
@app.trigger_handler
def toggle_mode():
    """Swap between moon and sun."""
    current = mode_state.get()
    mode_state.set("sun" if current == "moon" else "moon")
    # No return: auto-propagation re-renders the icon.


# --- Components ---
def IconDemo() -> Div:  # noqa: N802
    def dynamic_css() -> str:
        """Return a CSS string based on the current mode."""
        base = "w-12 h-12"
        if mode_state.get() == "moon":
            return f"{base} text-gray-300"
        return f"{base} text-yellow-500"

    return Div(
        Header("Icon Example", css=HEADER_CSS),
        Icon(
            lambda: MOON if mode_state.get() == "moon" else SUN,  # callable → re-evaluated on every render
            css=dynamic_css,  # callable → re-evaluated on every render
            listen_to="mode_state",  # re-render this icon when the mode changes
        ),
        Button(
            Icon(ARROWS_UP_DOWN, css="w-6 h-6 mr-2"),
            "Toggle",
            trigger="toggle_mode",
            css=f"inline-flex {BUTTON_PRIMARY_CSS}",
        ),
        css=BASE_CONTAINER_CSS,
    )


# --- Routes ---
@app.page("/")
def home():
    return IconDemo()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.icon_app:app", host="0.0.0.0", port=8000, reload=True)
