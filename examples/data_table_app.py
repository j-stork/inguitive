"""
Data Table Example using INGUITIVE framework.

Demonstrates:
- Rendering tabular data with the DataTable component
- Using list of dictionaries as the data structure
- Optional column ordering with the columns parameter
- Fine-grained CSS styling with dictionary-based css parameter
- Dynamic data rendering with state management

Features:
- Displays a table of employee data
- Shows three examples: default columns, custom column order, and custom CSS styling
- Table automatically updates when data changes

Run with: uvicorn examples.data_table_app:app --reload
"""

from pathlib import Path

from inguitive import DataTable, Div, State, Text, create_app

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent.parent / "templates")


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


# --- Components ---
def EmployeeTable():
    """Render employee data table with default column order."""
    return DataTable(
        data=employee_data_state.get,
        listen_to="employee_data_state",
        css="w-full border border-gray-200 rounded-lg",
    )


def EmployeeTableWithColumnOrder():
    """Render employee data table with custom column order."""
    return DataTable(
        data=employee_data_state.get,
        listen_to="employee_data_state",
        columns=["name", "department", "salary", "status"],  # id is omitted
        css="w-full border border-gray-200 rounded-lg",
    )


def EmployeeTableWithCustomCSS():
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


# --- Pages ---
@app.page("/")
def index():
    """Render the main data table example page."""
    return Div(
        Div(
            Text(
                "Data Table Example",
                css="text-3xl font-bold text-gray-900 mb-2",
            ),
            Text(
                "Demonstrates the DataTable component with list of dictionaries data structure.",
                css="text-lg text-gray-600 mb-8",
            ),
            
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
            
            # Information about the data structure
            Div(
                Text(
                    "Data Structure: List of Dictionaries",
                    css="text-lg font-semibold text-gray-800 mb-2",
                ),
                Text(
                    "Each row is a dictionary with column names as keys. "
                    "This is the most common format for tabular data in Python web applications, "
                    "matching JSON API responses and ORM query results.",
                    css="text-sm text-gray-600",
                ),
                css="p-6 bg-gray-50 rounded-lg border border-gray-200",
            ),
            
            css="w-full max-w-6xl mx-auto p-6",
        ),
        css="w-full bg-gray-100 min-h-screen",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.data_table_app:app", host="0.0.0.0", port=8000, reload=True)
