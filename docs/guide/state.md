# State System

inguitive's reactive state model is built around two containers:
**`State`** (global, shared across all sessions) and **`SessionState`**
(per-session, isolated per browser). When state changes, every component that
declared `listen_to` for that state object is automatically re-rendered via an
HTMX out-of-band swap — no JavaScript, no manual DOM manipulation.

## The two scopes

| | `State` | `SessionState` |
|---|---|---|
| Scope | Global (process-wide) | Per-session (isolated per browser) |
| `set()` pushes to | Every connected session (broadcast) | The current session only |
| Use case | Global counters, live metrics, server time | Per-user counters, per-user data, cart |

Scope is declared at construction time, not inferred from context. This
replaces the old implicit-scope model and removes a class of "which session
did I just write to?" bugs.

## Creating state

```python
from inguitive import State, SessionState

# Global — shared across all sessions
visitor_count = State(0, "visitor_count")
server_time   = State("", "server_time")

# Per-session — isolated per browser
counter    = SessionState(0, "counter")
user_name  = SessionState("", "user_name")
items      = SessionState([], "items")
settings   = SessionState({}, "settings")
```

The `name` parameter is required. It becomes the storage key in the
process-wide dict (`State`) or the session's data registry (`SessionState`)
and is stable across process restarts with a serializing backend (e.g.
`RedisBackend`). The name is not used for listener resolution — `listen_to`
takes the state object directly.

## Reading and writing

```python
# Read the current value
value = counter.get()

# Write a new value — returns None; propagation is automatic
counter.set(value + 1)
```

`.set()` returns `None`. The framework tracks state mutations during a trigger
handler's execution and, at handler exit, automatically collects the listener
component IDs of every mutated state and generates the OOB swap response. The
handler does not return OOB HTML — single-state and multi-state handlers are
equally simple.

For `State` (global), `set()` also broadcasts the update to every connected
session's SSE queues. For `SessionState`, `set()` pushes only to the current
session's queues.

## Per-session isolation with `SessionState`

Every browser session gets its own independent copy of a `SessionState`. The
`SessionState` instance is a module-level singleton, but its data is keyed by
the session ID injected by inguitive's session middleware.

```python
# This is safe — each user sees their own counter
counter = SessionState(0, "counter")

@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)   # affects only the caller's session
```

Two concurrent users will each see their own isolated counter, list, or dict.

## Global state with `State`

`State` holds a single process-wide value shared across all sessions. Use it
for server-wide data: live visitor counts, global metrics, server time.

```python
visitor_count = State(0, "visitor_count")

@ui.trigger_handler
def check_in():
    visitor_count.set(visitor_count.get() + 1)   # every connected tab updates
```

When `State.set()` is called from a background task (no session bound), the
update is broadcast to every connected session via SSE. When called inside a
trigger handler, the requesting session gets the OOB update in the HTTP
response immediately, and the broadcast delivers it to all other sessions via
SSE. See [SSE Workflow](sse.md) for the broadcast and per-session push recipes.

## Listening for changes

Add `listen_to` and `id` to any component that should re-render when state
changes. Pass the `State` or `SessionState` object itself — not a name string:

```python
Text(
    text=lambda: f"Items in cart: {cart.get()['count']}",
    id="cart-badge",
    listen_to=cart,          # single state object
)

Text(
    text=lambda: f"{first.get()} {last.get()}",
    id="full-name",
    listen_to=[first_name, last_name],   # multiple state objects
)
```

!!! tip "The `id` requirement"
    `id` is required for OOB swaps. inguitive uses the element's `id` to locate
    and replace exactly that element in the DOM. A component without an `id`
    will render on page load but will not receive live updates.

## Callable attributes

Because state reads happen at render time, all reactive values should be passed
as lambdas or other callables — not as evaluated strings:

```python
# Correct — lambda is called on every render
Text(text=lambda: f"Count: {counter.get()}", id="counter-label", listen_to=counter)

# Wrong — evaluated once at startup; never updates
Text(text=f"Count: {counter.get()}", id="counter-label", listen_to=counter)
```

## Mutable state (lists and dicts)

`.set()` replaces the stored value entirely. For mutable collections,
read, modify, then write:

```python
from inguitive import SessionState, get_trigger_args, get_form_data
from fastapi import Request

todos = SessionState([], "todos")


@ui.trigger_handler
async def add_todo(request: Request):
    form = await get_form_data(request)
    current = todos.get()
    todos.set(current + [{"text": form["text"], "done": False}])


@ui.trigger_handler
def toggle_todo():
    idx = int(get_trigger_args().get("idx", 0))
    current = todos.get()
    current[idx]["done"] = not current[idx]["done"]
    todos.set(list(current))   # set() triggers the re-render
```

## Auto-propagation: returning `None` vs `update_components`

Inside a trigger handler, `.set()` is enough — the framework detects the
mutation and renders the OOB response automatically. The handler returns
`None`:

```python
@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)
    # returns None — framework auto-generates the OOB swap
```

For the rare case where you need to push a component that was not triggered by
a state change, the explicit `update_components(*ids)` form is still
available:

```python
from inguitive import update_components

@ui.trigger_handler
def refresh():
    return update_components("chart", "status-badge")
```
