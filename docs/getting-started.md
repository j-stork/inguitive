# Getting Started

## Installation

```bash
pip install inguitive
```

For Redis-backed sessions (production):

```bash
pip install "inguitive[redis]"
```

## Scaffold a new app

The CLI creates a ready-to-run `app.py` in the current directory:

```bash
inguitive init
inguitive run
```

Then open [http://localhost:8000](http://localhost:8000).

`inguitive run` accepts `--host`, `--port`, and `--no-reload` flags and starts
uvicorn with auto-reload enabled by default.

## Your first app — step by step

### 1. Create the app

```python
from inguitive import create_app

app = create_app(title="My App")
```

`create_app` returns a FastAPI application with inguitive's session middleware,
HTMX routing, and Tailwind CDN wired in. The optional `title` and `favicon`
parameters control the browser tab; `head` accepts arbitrary HTML to inject
into `<head>`.

### 2. Define reactive state

```python
from inguitive import State

counter = State(0, "counter")
```

`State(initial_value, name)` creates a per-session reactive container. The name
must be unique across your app — it is used to route re-render notifications to
listening components.

### 3. Write a trigger handler

```python
@app.trigger_handler
def increment():
    counter.set(counter.get() + 1)
```

Trigger handlers are plain Python functions (sync or async) decorated with
`@app.trigger_handler`. inguitive registers an HTMX POST endpoint for each one
automatically.

### 4. Build a component

```python
from inguitive import Div, Label, Button
from inguitive.css import BUTTON_PRIMARY_CSS

def Counter():
    return Div(
        Label(
            text=lambda: f"Count: {counter.get()}",
            id="counter-label",
            listen_to="counter",
        ),
        Button("+1", trigger="increment", css=BUTTON_PRIMARY_CSS),
    )
```

Key points:

- `text=lambda: ...` — any attribute can be a callable; it is re-evaluated on every render.
- `listen_to="counter"` — when `counter` changes, the component is re-rendered via OOB swap.
- `id="counter-label"` — required for OOB swaps; must match the element in the DOM.

### 5. Define a page

```python
@app.page("/")
def index():
    return Counter()
```

`@app.page` registers a GET route. The return value is rendered into a full HTML
page with Tailwind and HTMX included.

For dynamic URLs with parameters, see [Routing and URL Parameters](guide/routing.md).

### 6. Run

```bash
inguitive run
# or
uvicorn app:app --reload
```

## Full counter example

```python
from inguitive import Div, Button, Label, State, create_app
from inguitive.css import BUTTON_PRIMARY_CSS

app = create_app(title="Counter")
counter = State(0, "counter")

@app.trigger_handler
def increment():
    counter.set(counter.get() + 1)

@app.trigger_handler
def decrement():
    counter.set(counter.get() - 1)

def Counter():
    return Div(
        Button("-1", trigger="decrement", css=BUTTON_PRIMARY_CSS),
        Label(
            text=lambda: str(counter.get()),
            id="counter-label",
            listen_to="counter",
            css="text-4xl font-bold mx-4",
        ),
        Button("+1", trigger="increment", css=BUTTON_PRIMARY_CSS),
        css="flex items-center gap-4 p-8",
    )

@app.page("/", title="Counter")
def index():
    return Counter()
```

## Next steps

- [Components](guide/components.md) — the full component library
- [Routing and URL Parameters](guide/routing.md) — dynamic URLs with type validation
- [Reactive State](guide/state.md) — how state isolation and propagation work
- [Trigger Handlers](guide/trigger-handlers.md) — trigger args, async handlers, form data
- [Form Validation](guide/form-validation.md) — declarative schemas with `FormSchema`
- [Session Backends](guide/session-backends.md) — scaling to production
