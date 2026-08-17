# Examples

All examples live in the `examples/` directory of the repository and can be
run directly with `inguitive run` or `uvicorn`.

## Counter app

**File:** `examples/counter_app.py`

Per-session counter with a theme toggle. Demonstrates:

- `State` with `get()` / `set()`
- `listen_to` for automatic re-rendering
- Dynamic CSS with callables
- Two trigger handlers sharing one state object

```bash
uvicorn examples.counter_app:app --reload
```

## Todo app

**File:** `examples/todo_app.py`

Full CRUD task list with filtering and a live item count. Demonstrates:

- List state (`State([], "todos")`)
- Conditional rendering with lambdas
- Multiple components listening to the same state
- Filtering without a page reload

```bash
uvicorn examples.todo_app:app --reload
```

## Chat app

**File:** `examples/chat_app.py`

Real-time chat using shared state. Demonstrates:

- State shared across sessions (module-level list)
- Append-only state mutation pattern
- `listen_to` with a high-frequency update state

```bash
uvicorn examples.chat_app:app --reload
```

## Data table app

**File:** `examples/data_table_app.py`

Sortable, filterable table with `DataTable`. Demonstrates:

- `DataTable` with a `css` dict for granular styling
- `trigger_args` for passing column sort keys
- Stateful sort direction toggle

```bash
uvicorn examples.data_table_app:app --reload
```

## Registration form

**File:** `examples/registration_form.py`

Form handling with `Form`, `Input`, and `Textarea`. Demonstrates:

- Collecting multipart form data in a trigger handler
- Displaying validation errors inline
- `FormSchema` + `validate_form` for declarative validation

```bash
uvicorn examples.registration_form:app --reload
```

## Navigation demo

**File:** `examples/navigation_demo.py`

Side-by-side comparison of `Link` vs `trigger`. Demonstrates:

- When to use `Link(href=...)` (URL changes, new tab)
- When to use `trigger=...` (partial page update, no URL change)

```bash
uvicorn examples.navigation_demo:app --reload
```
