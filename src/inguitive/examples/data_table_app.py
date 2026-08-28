"""
DataTable example using inguitive.

Run with: uvicorn inguitive.examples.data_table_app:app --reload

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
   ``listen_to=["people_state", "columns_state", "style_state"]`` so it
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

from inguitive import Button, DataTable, Div, Header, State, create_app

from .css import BASE_CONTAINER_CSS, BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS, HEADER_CSS

# --- App Setup ---
app = create_app()


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
@app.trigger_handler
def reorder_columns():
    """Toggle between default column order and a reversed order (no id)."""
    current = columns_state.get()
    if current is None:
        # Reverse the order and drop id so the change is visually obvious.
        columns_state.set(["city", "role", "name"])
    else:
        columns_state.set(None)


@app.trigger_handler
def toggle_style():
    """Toggle between default and custom dict-based styling."""
    current = style_state.get()
    style_state.set("custom" if current == "default" else "default")


@app.trigger_handler
def reset():
    """Reset both columns and styling to defaults."""
    columns_state.set(None)
    style_state.set("default")


# --- Components ---
def table_css():
    """Return DataTable css: plain string for default, dict for custom.

    The dict form maps sub-element keys ("table", "header", "row", "cell")
    to CSS classes — the DataTable-specific feature this example highlights.
    """
    if style_state.get() == "custom":
        return {
            "table": "w-full max-w-4xl mx-auto border border-yellow-500",
            "header": "px-3 py-2 bg-yellow-500 font-mono uppercase",
            "row": "hover:bg-white/20 transition-colors",
            "cell": "px-3 py-2 border border-yellow-500 text-white font-mono",
        }
    return "w-full max-w-4xl mx-auto text-left"


def PeopleTable() -> DataTable:  # noqa: N802
    """Single table reacting to three states via multi-state listen_to."""
    return DataTable(
        data=lambda: people_state.get(),
        columns=lambda: columns_state.get(),
        css=table_css,
        listen_to=["people_state", "columns_state", "style_state"],
    )


def Controls() -> Div:  # noqa: N802
    return Div(
        Button("Reorder columns", trigger="reorder_columns", css=BUTTON_PRIMARY_CSS),
        Button("Custom styling", trigger="toggle_style", css=BUTTON_PRIMARY_CSS),
        Button("Reset", trigger="reset", css=BUTTON_SECONDARY_CSS),
        css="flex gap-6 w-full max-w-4xl mx-auto",
    )


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Header("Data Table Example", css=HEADER_CSS),
        Controls(),
        PeopleTable(),
        css=BASE_CONTAINER_CSS,
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.data_table_app:app", host="0.0.0.0", port=8000, reload=True)
