"""
DataTable example using inguitive.

Run with: uvicorn examples.data_table_app:app --reload

The DataTable Component
-----------------------
This example demonstrates the ``DataTable`` component, which renders a list
of dictionaries as an HTML table. Three DataTable-specific capabilities are
exercised here:

1. **Data from a callable.** ``data`` accepts a zero-argument callable
   returning a ``list[dict]`` (here ``people_state.get``), re-evaluated on
   every render so the table reflects the current state.

2. **Dynamic columns via a callable.** ``columns`` accepts a callable
   returning a ``list[str]`` (or ``None`` to fall back to the first row's
   keys). The "Reorder columns" button toggles between ``None`` (default
   order) and a reversed order that omits the ``id`` column.

3. **Dictionary CSS for fine-grained styling.** ``css`` accepts a dict with
   ``"table"``, ``"header"``, ``"row"``, and ``"cell"`` keys, each mapping to
   CSS classes for that sub-element. The "Custom styling" button swaps
   between the default styling and a dict that styles each part of the
   table separately.

4. **Multi-state ``listen_to``.** The single table declares
   ``listen_to=[people_state, columns_state, style_state]`` so it
   re-renders when any of the three states changes — one component reacting
   to multiple states.

All handlers return nothing: auto-propagation (see
``auto_propagation_app.py``) re-renders the table after each toggle.

To test:
1. The table shows three people with default column order and styling
2. Click "Reorder columns" — the id column disappears, order changes
3. Click "Custom styling" — header, rows, and cells get distinct colours
4. Click "Reset" — both revert to defaults
"""

from fastapi import FastAPI

from inguitive import Button, DataTable, Div, State, UI

from .css import (
    BRAND_COLORS,
    BUTTON_PRIMARY_BLUE_CSS,
    BUTTON_PRIMARY_YELLOW_CSS,
    BUTTON_SECONDARY_CSS,
)
from .custom_components import BaseContainer, Card, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- Sample Data ---
PEOPLE = [
    {"id": 1, "name": "Alice", "role": "Engineer", "city": "Berlin"},
    {"id": 2, "name": "Bob", "role": "Designer", "city": "Paris"},
    {"id": 3, "name": "Cara", "role": "Manager", "city": "Rome"},
]


# --- State Instances ---
people_state = State(PEOPLE, "people_state")
# None = default column order (keys from the first row); list = custom order.
columns_state: State[list[str] | None] = State(None, "columns_state")
# "default" = no css dict; "custom" = dict-based fine-grained styling.
style_state: State[str] = State("default", "style_state")


# --- Trigger Handlers ---
@ui.trigger_handler
def reorder_columns():
    """Toggle between default column order and a reversed order (no id)."""
    current = columns_state.get()
    if current is None:
        # Reverse the order and drop id so the change is visually obvious.
        columns_state.set(["city", "role", "name"])
    else:
        columns_state.set(None)


@ui.trigger_handler
def toggle_style():
    """Toggle between default and custom dict-based styling."""
    current = style_state.get()
    style_state.set("custom" if current == "default" else "default")


@ui.trigger_handler
def reset():
    """Reset both columns and styling to defaults."""
    columns_state.set(None)
    style_state.set("default")


# --- Components ---
def PeopleTable() -> DataTable:  # noqa: N802
    """Single table reacting to three states via multi-state listen_to."""

    def dynamic_css():
        """Return DataTable css: plain string for default, dict for custom.

        The dict form maps sub-element keys ("table", "header", "row", "cell")
        to CSS classes — the DataTable-specific feature this example highlights.
        """
        if style_state.get() == "custom":
            return {
                "table": f"w-full border border-{BRAND_COLORS['yellow']}",
                "header": f"px-3 py-2 font-mono uppercase bg-{BRAND_COLORS['yellow']} text-black/80",
                "row": f"hover:bg-{BRAND_COLORS['background_2']} transition-colors",
                "cell": f"px-3 py-2 font-mono border border-{BRAND_COLORS['yellow']} text-{BRAND_COLORS['text_0']}",
            }
        return "w-full"

    return DataTable(
        data=lambda: people_state.get(),
        columns=lambda: columns_state.get(),
        css=dynamic_css,
        listen_to=[people_state, columns_state, style_state],
    )


def Controls() -> Div:  # noqa: N802
    return Div(
        Button("Reorder columns", trigger=reorder_columns, css=BUTTON_PRIMARY_BLUE_CSS),
        Button("Custom styling", trigger=toggle_style, css=BUTTON_PRIMARY_YELLOW_CSS),
        Button("Reset", trigger=reset, css=BUTTON_SECONDARY_CSS),
        css="grid grid-cols-3 gap-6 w-full",
    )


# --- Routes ---
@app.get("/")
def home():
    return ui.page(BaseContainer(
        InguitiveLogo(),
        Title("Data Table Example"),
        Card(
            Controls(),
            PeopleTable(),
        ),
    ))


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.data_table_app:app", host="0.0.0.0", port=8000, reload=True)
