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
   render. Here ``icon_svg`` switches between ``MOON`` and ``SUN`` based on
   ``mode_state``, so a single ``Icon`` component swaps its glyph when the
   state changes.

The button toggles ``mode_state``; the icon re-renders via auto-propagation
(see ``auto_propagation_app.py``). Contrast with ``counter_app.py``, where
dynamic attributes are shown on ``Text`` and ``Div`` rather than on ``Icon``.

To test:
1. The page shows a moon icon and a "Toggle" button
2. Click the button — the icon swaps to a sun
3. Click again — it swaps back to a moon
"""

from markupsafe import Markup

from inguitive import Button, Div, Icon, State, create_app

from .css import BUTTON_PRIMARY_CSS
from .svg import MOON, SUN

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
def icon_svg() -> Markup:
    """Return the SVG markup for the current mode."""
    return MOON if mode_state.get() == "moon" else SUN


def IconDemo() -> Div:  # noqa: N802
    return Div(
        Icon(
            icon_svg,  # callable → re-evaluated on every render
            css="w-12 h-12 text-slate-700",
            listen_to="mode_state",  # re-render this icon when the mode changes
        ),
        Button("Toggle", trigger="toggle_mode", css=BUTTON_PRIMARY_CSS),
        css="flex flex-col items-center gap-6 p-6",
    )


# --- Routes ---
@app.page("/")
def home():
    return Div(
        IconDemo(),
        css="min-h-screen flex items-center justify-center bg-slate-100",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.icon_app:app", host="0.0.0.0", port=8000, reload=True)
