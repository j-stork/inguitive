# Reactive State

inguitive's `State` container is the core of the reactivity model. When state
changes, every component that declared `listen_to` for that state name is
automatically re-rendered via an HTMX out-of-band swap — no JavaScript, no
manual DOM manipulation.

## Creating state

```python
from inguitive import State

# State(initial_value, name)
counter   = State(0,    "counter")
user_name = State("",   "user_name")
items     = State([],   "items")
settings  = State({},   "settings")
```

The `name` must be unique across your application. It is the key used to route
re-render notifications to listening components, so duplicate names cause
components to re-render on the wrong state changes.

## Reading and writing

```python
# Read the current value for the active session
value = counter.get()

# Write a new value — triggers re-render for all listeners
counter.set(value + 1)
```

Both `get()` and `set()` operate on the **current session's** state. Two
concurrent users will each see their own isolated counter, list, or dict.

## Per-session isolation

Every browser session gets its own independent copy of every `State` object.
The `State` instance itself is a module-level singleton, but its data is keyed
by the session ID injected by inguitive's session middleware.

```python
# This is safe — each user sees their own counter
counter = State(0, "counter")

@app.trigger_handler
def increment():
    counter.set(counter.get() + 1)   # affects only the caller's session
```

!!! warning "Shared state"
    If you genuinely want state shared across all sessions (e.g. a live visitor
    count), store it in a database or external store and read it in your handler.
    Mutating a plain Python module-level variable is not thread-safe and will not
    survive a process restart.

## Listening for changes

Add `listen_to` and `id` to any component that should re-render when state
changes:

```python
Label(
    text=lambda: f"Items in cart: {cart.get()['count']}",
    id="cart-badge",
    listen_to="cart",         # single state name
)

Text(
    text=lambda: f"{first.get()} {last.get()}",
    id="full-name",
    listen_to=["first_name", "last_name"],   # multiple state names
)
```

!!! tip "The `id` requirement"
    `id` is required for OOB swaps. inguitive uses the element's `id` to locate
    and replace exactly that element in the DOM. A component without an `id` will
    render on page load but will not receive live updates.

## Callable attributes

Because state reads happen at render time, all reactive values should be passed
as lambdas or other callables — not as evaluated strings:

```python
# ✅ Correct — lambda is called on every render
Label(text=lambda: f"Count: {counter.get()}", id="counter-label", listen_to="counter")

# ❌ Wrong — evaluated once at startup; never updates
Label(text=f"Count: {counter.get()}", id="counter-label", listen_to="counter")
```

## Mutable state (lists and dicts)

`State.set()` replaces the stored value entirely. For mutable collections,
read, modify, then write:

```python
todos = State([], "todos")

@app.trigger_handler
def add_todo(form_data: dict):
    current = todos.get()
    todos.set(current + [{"text": form_data["text"], "done": False}])

@app.trigger_handler
def toggle_todo():
    idx = int(get_trigger_args().get("idx", 0))
    current = todos.get()
    current[idx]["done"] = not current[idx]["done"]
    todos.set(list(current))   # set() triggers the re-render
```
