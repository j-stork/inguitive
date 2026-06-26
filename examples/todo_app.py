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
from inguitive.css import BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent / "templates")


# --- State Instances ---
# Single state for all todo data: {"todos": [...], "filter": "all" | "active" | "completed"}
todo_state = State({"todos": [], "filter": "all"}, "todo_state")


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


def TodoItem(todo: dict) -> Div:
    """Render a single todo item with checkbox, title, and delete button."""
    return Div(
        Checkbox(
            id=f"todo-{todo['id']}",
            checked=todo["completed"],
            trigger="toggle_todo",
            trigger_args={"id": todo["id"]},
            name="completed",
            css="h-5 w-5 cursor-pointer",
        ),
        Text(
            todo["title"],
            css="flex-1 " + ("line-through text-gray-400" if todo["completed"] else "text-gray-800"),
        ),
        Button(
            "×",
            trigger="delete_todo",
            trigger_args={"id": todo["id"]},
            css="text-red-500 hover:text-red-700 px-2 py-1",
        ),
        css="flex items-center gap-3 p-2 border-b border-gray-200 last:border-b-0",
    )


def TodoForm() -> Form:
    """Form for adding new todos."""
    return Form(
        Div(
            Input(
                id="todo-input",
                name="title",
                placeholder="What needs to be done?",
                css="flex-1 p-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-blue-500",
            ),
            Button(
                "Add",
                type="submit",
                css=f"{BUTTON_PRIMARY_CSS} rounded-l-none",
            ),
            css="flex gap-0",
        ),
        trigger="add_todo",
        css="mb-4",
    )


def TodoList() -> Div:
    """Render the list of todos based on the current filter."""
    def render_todos() -> list:
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
            return [Text("No todos found.", css="text-gray-500 p-4 text-center")]

        return [TodoItem(todo) for todo in filtered_todos]

    return Div(
        lambda: render_todos(),
        id="todo_list",
        listen_to="todo_state",
        css="border border-gray-200 rounded-md overflow-hidden",
    )


def TodoFilters() -> Div:
    """Filter controls for the todo list."""
    
    def get_filter_button_css(filter_name: str) -> str:
        """Return CSS classes for filter button with active state."""
        current_filter = todo_state.get()["filter"]
        base = f"{BUTTON_SECONDARY_CSS} px-4 py-2"
        if current_filter == filter_name:
            return f"{base} ring-2 ring-blue-500"
        return base

    return Div(
        Button(
            "All",
            trigger="set_filter",
            trigger_args={"filter": "all"},
            css=lambda: get_filter_button_css("all"),
            listen_to="todo_state",
        ),
        Button(
            "Active",
            id="active_filter_button",
            trigger="set_filter",
            trigger_args={"filter": "active"},
            css=lambda: get_filter_button_css("active"),
            listen_to="todo_state",
        ),
        Button(
            "Completed",
            trigger="set_filter",
            trigger_args={"filter": "completed"},
            css=lambda: get_filter_button_css("completed"),
            listen_to="todo_state",
        ),
        css="flex gap-2 mb-4",
        id="filter_buttons",
    )


def TodoCount() -> Text:
    """Display the count of remaining active todos."""
    todos = todo_state.get()["todos"]
    active_count = sum(1 for t in todos if not t["completed"])
    item_word = "item" if active_count == 1 else "items"
    return Text(
        f"{active_count} {item_word} left",
        id="todo_count",
        css="text-sm text-gray-500",
        listen_to="todo_state",
    )


def TodoApp() -> Div:
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
                    css=BUTTON_SECONDARY_CSS,
                ),
                css="mt-4 flex justify-center",
            ),
            id="todo_container",
            css="max-w-md mx-auto p-6 bg-white rounded-xl shadow-md space-y-4 w-full",
        ),
        css="w-full min-h-screen flex items-center justify-center p-4 bg-gray-50",
    )


# --- Routes ---
@app.page("/")
def home():
    return TodoApp()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.todo_app:app", host="0.0.0.0", port=8000, reload=True)
