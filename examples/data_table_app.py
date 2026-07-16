"""
Data Table Example using INGUITIVE framework.

Demonstrates:
- Rendering tabular data with the DataTable component
- Using list of dictionaries as the data structure
- Optional column ordering with the columns parameter
- Fine-grained CSS styling with dictionary-based css parameter
- Dynamic data rendering with state management
- Table sorting with toggleable ascending/descending order
- Auto-propagation of state updates (automatic OOB response generation)
- Using get_trigger_args() to access trigger arguments
- Free-text filtering with conditional reset button and status display
- State-based UI controls (show/hide status text and reset button)

Features:
- Displays a table of employee data
- Sort controls with buttons for each column
- Click a button to sort ascending, click again to sort descending
- Free-text filter across all fields with status display and conditional reset button
- Status text shows "Filter is applied: <text>" when a filter is active
- Reset button appears only when filter is active
- Shows three examples: default columns, custom column order, and custom CSS styling
- Table automatically updates when data changes
- Auto-generated OOB responses from state mutations
- Trigger handlers access arguments via get_trigger_args() without form_data parameter
- Form submission with form_data for dynamic input

Run with: uvicorn examples.data_table_app:app --reload
"""

from pathlib import Path

from inguitive import Button, DataTable, Div, Form, Input, State, Text, create_app, get_trigger_args

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent.parent / "templates")


# --- CSS ---
COLOR_BASE = "slate"
COLOR_100 = f"{COLOR_BASE}-100"
COLOR_200 = f"{COLOR_BASE}-200"
COLOR_300 = f"{COLOR_BASE}-300"
COLOR_400 = f"{COLOR_BASE}-400"
COLOR_900 = f"{COLOR_BASE}-900"
COLOR_BRAND_1 = "blue-700"
COLOR_BRAND_2 = "fuchsia-600"
COLOR_BRAND_2_LIGHT = "fuchsia-500"
BUTTON_SHAPE = "px-3 py-2 rounded-md font-semibold cursor-pointer shadow-lg active:shadow-none"
BUTTON_PRIMARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_BRAND_1} to-{COLOR_BRAND_2} text-{COLOR_100} hover:to-{COLOR_BRAND_2_LIGHT}"
BUTTON_SECONDARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_400} to-{COLOR_300} text-{COLOR_900} hover:to-{COLOR_200}"


# --- Sample Data ---
# Employee data as list of dictionaries
EMPLOYEE_DATA = [
    {"id": 1, "name": "Alice Johnson", "department": "Engineering", "salary": 75000, "status": "Active"},
    {"id": 2, "name": "Bob Smith", "department": "Sales", "salary": 65000, "status": "Active"},
    {"id": 3, "name": "Charlie Brown", "department": "Engineering", "salary": 80000, "status": "Active"},
    {"id": 4, "name": "Diana Prince", "department": "Marketing", "salary": 68000, "status": "On Leave"},
    {"id": 5, "name": "Eve Adams", "department": "HR", "salary": 72000, "status": "Active"},
    {"id": 6, "name": "Frank Castle", "department": "Engineering", "salary": 85000, "status": "Active"},
]

# State to store table data (allows dynamic updates)
employee_data_state = State(EMPLOYEE_DATA, "employee_data_state")

# State to track sort configuration
sort_config_state = State({"column": None, "direction": "asc"}, "sort_config_state")

# State to track filter text (empty string = no filter)
filter_text_state = State("", "filter_text_state")


# --- Trigger Handlers ---
@app.trigger_handler
def sort_employees():
    """Sort employee table by specified column. Toggles direction on repeated clicks.

    Demonstrates auto-propagation and get_trigger_args() for accessing
    trigger arguments without form_data parameter.
    """
    column = get_trigger_args().get("column")
    if not column:
        return ""

    # Get current sort config
    current_config = sort_config_state.get()
    current_column = current_config.get("column")

    # Determine new direction
    if current_column == column:
        # Same column: toggle direction
        new_direction = "desc" if current_config.get("direction") == "asc" else "asc"
    else:
        # Different column: start with ascending
        new_direction = "asc"

    # Update sort config
    sort_config_state.set({"column": column, "direction": new_direction})

    # Sort the data (copy to avoid mutating original)
    data = list(employee_data_state.get())
    if column and column != "none":
        # Handle None values and missing keys safely
        data.sort(key=lambda x: str(x.get(column, "") or ""), reverse=(new_direction == "desc"))

    # Update data state - auto-propagation will handle OOB response
    employee_data_state.set(data)

    # No explicit return - auto-propagation generates response automatically


@app.trigger_handler
def filter_employees(form_data: dict):
    """Filter employees by text search across all fields.

    Searches all string values in each employee dictionary for the
    filter text (case-insensitive). Sets filter_text_state to the search
    text when filter is applied, empty string when cleared.

    Demonstrates:
    - Form data access via form_data parameter
    - Free-text search across multiple fields
    - State management for UI feedback
    """
    search_text = form_data.get("filter-text", "").lower()

    if search_text:
        # Filter data: search across all fields
        filtered = [e for e in EMPLOYEE_DATA if any(search_text in str(v).lower() for v in e.values())]
        filter_text_state.set(search_text)
    else:
        # Empty search = show all (clear filter)
        filtered = list(EMPLOYEE_DATA)
        filter_text_state.set("")

    employee_data_state.set(filtered)
    # Auto-propagation handles OOB response - no explicit return needed


@app.trigger_handler
def clear_filter():
    """Clear the current filter, showing all employees.

    Resets employee data to full list and clears filter_text_state.
    """
    filter_text_state.set("")
    employee_data_state.set(list(EMPLOYEE_DATA))
    # Auto-propagation handles OOB response - no explicit return needed


# --- Components ---
def EmployeeTable():  # noqa: N802
    """Render employee data table with default column order."""
    return DataTable(
        data=employee_data_state.get,
        listen_to="employee_data_state",
        css="w-full border border-gray-200 rounded-lg",
    )


def EmployeeTableWithColumnOrder():  # noqa: N802
    """Render employee data table with custom column order."""
    return DataTable(
        data=employee_data_state.get,
        listen_to="employee_data_state",
        columns=["name", "department", "salary", "status"],  # id is omitted
        css="w-full border border-gray-200 rounded-lg",
    )


def EmployeeTableWithCustomCSS():  # noqa: N802
    """Render employee data table with custom CSS for sub-elements."""
    return DataTable(
        data=employee_data_state.get,
        listen_to="employee_data_state",
        columns=["name", "department", "salary", "status"],
        css={
            "table": "w-full border-2 border-blue-600 rounded-lg",
            "header": "px-4 py-3 bg-blue-600 text-white font-bold text-sm",
            "cell": "px-4 py-3 border border-blue-200",
            "row": "hover:bg-blue-50 transition-colors",
        },
    )


def SortButtons():  # noqa: N802
    """Render sort buttons for each column in the employee table."""
    # Column names and their display labels
    columns = ["id", "name", "department", "salary", "status"]
    column_labels = ["ID", "Name", "Department", "Salary", "Status"]

    buttons = []
    for col, label in zip(columns, column_labels):
        buttons.append(
            Button(
                label,
                trigger="sort_employees",
                trigger_args={"column": col},
                css=BUTTON_SECONDARY,
            )
        )

    return Div(
        Text(
            "Sort tables by:", 
            css=f"font-medium text-{COLOR_300}",
        ),
        Div(
            *buttons, 
            css="flex flex-wrap gap-3"
        ),
        css="space-y-3",
    )


def FilterControls():  # noqa: N802
    """Filter UI with input field, status text, and conditional reset button.

    Demonstrates:
    - Form component with Input and Button
    - Conditional rendering based on state (status text and reset button)
    - Trigger handlers for form submission
    - Free-text search across all fields
    - State-based conditional UI with text display
    """

    def dynamic_text():
        """Return status text based on whether filter is applied."""
        filter_text = filter_text_state.get()
        if filter_text:
            return f"Filter is applied: {filter_text}"
        return ""

    def dynamic_div_css():
        """Return CSS for status div based on whether filter is applied."""
        if filter_text_state.get():
            return "flex items-center gap-3"
        return "hidden"

    return Div(
        Text(
            "Filter:", 
            css=f"font-medium text-{COLOR_300}",
        ),
        Form(
            Input(
                id="filter-text",
                name="filter-text",
                placeholder="Filter by any keyword...",
                css=f"px-3 py-2 bg-{COLOR_300} rounded-md",
            ),
            Button(
                "Filter",
                type="submit",
                css=BUTTON_PRIMARY,
            ),
            trigger="filter_employees",
            css="flex items-center gap-3",
        ),
        Div(
            Text(
                dynamic_text,
                css=f"text-{COLOR_300}",
            ),
            Button(
                "Reset",
                trigger="clear_filter",
                listen_to="filter_text_state",
                css=BUTTON_SECONDARY,
            ),
            listen_to="filter_text_state",
            css=dynamic_div_css,
        ),
        css="space-y-3",
    )


# --- Pages ---
@app.page("/")
def index():
    """Render the main data table example page."""
    return Div(
        Div(
            Div(
                Text(
                    "Data Table Example",
                    css=f"text-3xl font-bold text-{COLOR_100}",
                ),
                Text(
                    "Demonstrates the DataTable component with list of dictionaries data structure.",
                    css=f"text-lg text-{COLOR_300}",
                ),
            ),
            # Sort controls
            SortButtons(),
            # Filter controls
            FilterControls(),
            # First example: Default columns (natural order)
            Div(
                Text(
                    "Example 1: Default Column Order",
                    css="text-xl font-semibold text-gray-800 mb-4",
                ),
                Text(
                    "Columns are automatically extracted from the first row's keys in insertion order.",
                    css="text-sm text-gray-500 mb-3",
                ),
                EmployeeTable(),
                css="mb-12",
            ),
            # Second example: Custom column order
            Div(
                Text(
                    "Example 2: Custom Column Order",
                    css="text-xl font-semibold text-gray-800 mb-4",
                ),
                Text(
                    "Use the 'columns' parameter to control order and select which columns to display.",
                    css="text-sm text-gray-500 mb-3",
                ),
                EmployeeTableWithColumnOrder(),
                css="mb-12",
            ),
            # Third example: Custom CSS with dictionary
            Div(
                Text(
                    "Example 3: Custom CSS Styling",
                    css="text-xl font-semibold text-gray-800 mb-4",
                ),
                Text(
                    "Use a dictionary for the 'css' parameter to style sub-elements independently: "
                    "'table', 'header', 'cell', and 'row'.",
                    css="text-sm text-gray-500 mb-3",
                ),
                EmployeeTableWithCustomCSS(),
                css="mb-12",
            ),
            css="w-full max-w-6xl mx-auto p-6 space-y-6",
        ),
        css=f"w-full bg-{COLOR_900} min-h-screen",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.data_table_app:app", host="0.0.0.0", port=8000, reload=True)
