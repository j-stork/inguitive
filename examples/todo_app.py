"""
Todo App example using INGUITIVE framework.

Demonstrates CRUD operations (Create, Read, Update, Delete) with reactive state management.

Features:
- Add new todos
- Mark todos as complete/incomplete
- Delete todos
- Filter by status (All/Active/Completed)
- Clear all completed todos
- Real-time count of remaining items
- Session isolation (each browser tab has independent state)

Run with: uvicorn examples.todo_app:app --reload
"""

import uuid
from pathlib import Path

from inguitive import (
    Button,
    Checkbox,
    Div,
    Form,
    Input,
    State,
    Text,
    create_app,
    update_components,
)

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent / "templates")


# --- State Instances ---
# Single state for all todo data: {"todos": [...], "filter": "all" | "active" | "completed"}
todo_state = State({"todos": [], "filter": "all"}, "todo_state")


# --- CSS ---
COLOR_PRIMARY = "slate-600"
COLOR_SECONDARY = "slate-300"
COLOR_ACTIVE = "amber-300"
BUTTON_SHAPE = "px-3 py-2 rounded-md font-semibold cursor-pointer"


# --- Trigger Handlers ---
@app.trigger_handler
async def add_todo(form_data: dict) -> str:
    """Add a new todo item to the list."""
    current = todo_state.get()
    new_todo = {
        "id": str(uuid.uuid4()),
        "title": form_data.get("title", "").strip(),
        "completed": False,
    }
    # Only add if title is not empty
    if new_todo["title"]:
        current["todos"].append(new_todo)
        todo_state.set(current)
        return update_components(*todo_state.listeners)
    return ""


@app.trigger_handler
async def toggle_todo(form_data: dict) -> str:
    """Toggle the completed status of a todo."""
    current = todo_state.get()
    todo_id = form_data.get("id")
    if todo_id:
        for todo in current["todos"]:
            if todo["id"] == todo_id:
                todo["completed"] = not todo["completed"]
                break
        todo_state.set(current)
        return update_components(*todo_state.listeners)
    return ""


@app.trigger_handler
async def delete_todo(form_data: dict) -> str:
    """Delete a todo item from the list."""
    current = todo_state.get()
    todo_id = form_data.get("id")
    if todo_id:
        current["todos"] = [t for t in current["todos"] if t["id"] != todo_id]
        todo_state.set(current)
        return update_components(*todo_state.listeners)
    return ""


@app.trigger_handler
async def set_filter(form_data: dict) -> str:
    """Set the filter for the todo list (all/active/completed)."""
    current = todo_state.get()
    new_filter = form_data.get("filter", "all")
    if new_filter in ("all", "active", "completed"):
        current["filter"] = new_filter
        todo_state.set(current)
        return update_components(*todo_state.listeners)
    return ""


@app.trigger_handler
async def clear_completed(form_data: dict) -> str:
    """Remove all completed todos from the list."""
    current = todo_state.get()
    current["todos"] = [t for t in current["todos"] if not t["completed"]]
    todo_state.set(current)
    return update_components(*todo_state.listeners)


# --- Component Functions ---


def TodoItem(todo: dict) -> Div:  # noqa: N802
    """Render a single todo item with checkbox, title, and delete button."""

    def dynamic_div_css():
        base = f"flex items-center gap-3 p-3 border-b border-{COLOR_SECONDARY} last:border-b-0"
        if todo["completed"]:
            return f"{base} bg-green-300"
        return base

    return Div(
        Checkbox(
            id=f"todo-{todo['id']}",
            checked=lambda: todo["completed"],
            trigger="toggle_todo",
            trigger_args={"id": todo["id"]},
            name="completed",
            css="h-5 w-5 cursor-pointer",
        ),
        Text(
            lambda: todo["title"],
            css=lambda: "flex-1" + (" line-through" if todo["completed"] else ""),
        ),
        Button(
            "Delete",
            trigger="delete_todo",
            trigger_args={"id": todo["id"]},
            css="underline cursor-pointer",
        ),
        css=lambda: dynamic_div_css(),
    )


def TodoForm() -> Form:  # noqa: N802
    """Form for adding new todos."""
    return Form(
        Input(
            id="todo-input",
            name="title",
            placeholder="What needs to be done?",
            css=f"flex-1 p-2 border border-{COLOR_SECONDARY} rounded-md",
        ),
        Button(
            "Add",
            type="submit",
            css=f"{BUTTON_SHAPE} bg-{COLOR_PRIMARY} text-white",
        ),
        trigger="add_todo",
        css="flex gap-3",
    )


def TodoList() -> Div:  # noqa: N802
    """Render the list of todos based on the current filter."""

    def dynamic_content() -> list:
        """Return list of todo item components based on current state."""
        data = todo_state.get()
        todos = data["todos"]
        filter_type = data["filter"]

        # Filter todos based on current filter
        filtered_todos = {
            "all": todos,
            "active": [t for t in todos if not t["completed"]],
            "completed": [t for t in todos if t["completed"]],
        }.get(filter_type, todos)

        if not filtered_todos:
            return [Text("No todos found.", css="p-3 text-center")]

        return [TodoItem(todo) for todo in filtered_todos]

    return Div(
        lambda: dynamic_content(),
        id="todo_list",
        listen_to="todo_state",
        css=f"border border-{COLOR_SECONDARY} rounded-md overflow-hidden",
    )


def TodoFilters() -> Div:  # noqa: N802
    """Filter controls for the todo list."""

    def dynamic_css(filter_name: str) -> str:
        """Return CSS classes for filter button with active state."""
        current_filter = todo_state.get()["filter"]
        if current_filter == filter_name:
            return f"{BUTTON_SHAPE} bg-{COLOR_ACTIVE}"
        return f"{BUTTON_SHAPE} bg-{COLOR_SECONDARY}"

    return Div(
        Button(
            "All",
            trigger="set_filter",
            trigger_args={"filter": "all"},
            css=lambda: dynamic_css("all"),
            listen_to="todo_state",
        ),
        Button(
            "Active",
            id="active_filter_button",
            trigger="set_filter",
            trigger_args={"filter": "active"},
            css=lambda: dynamic_css("active"),
            listen_to="todo_state",
        ),
        Button(
            "Completed",
            trigger="set_filter",
            trigger_args={"filter": "completed"},
            css=lambda: dynamic_css("completed"),
            listen_to="todo_state",
        ),
        css="grid grid-cols-3 gap-x-3",
        id="filter_buttons",
    )


def TodoCount() -> Text:  # noqa: N802
    """Display the count of remaining active todos."""

    def dynamic_text() -> str:
        todos = todo_state.get()["todos"]
        active_count = sum(1 for t in todos if not t["completed"])
        item_word = "item" if active_count == 1 else "items"
        return f"{active_count} {item_word} left"

    return Text(
        lambda: dynamic_text(),
        id="todo_count",
        listen_to="todo_state",
    )


def TodoApp() -> Div:  # noqa: N802
    """Main todo application component."""
    return Div(
        Div(
            Text("Todo App", css="text-2xl font-bold mb-4 text-center"),
            TodoForm(),
            TodoFilters(),
            TodoCount(),
            TodoList(),
            Div(
                Button(
                    "Clear Completed",
                    trigger="clear_completed",
                    css=f"{BUTTON_SHAPE} bg-{COLOR_SECONDARY}",
                ),
                css="flex justify-center",
            ),
            id="todo_container",
            css="max-w-md mx-auto p-6 bg-white rounded-xl shadow-md space-y-6 w-full",
        ),
        css="w-full min-h-screen flex items-center justify-center bg-slate-100",
    )


# --- Routes ---
@app.page("/")
def home():
    return TodoApp()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.todo_app:app", host="0.0.0.0", port=8000, reload=True)
