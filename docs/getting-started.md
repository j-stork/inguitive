# Getting Started

## Installation

```bash
pip install inguitive
```

For Redis-backed sessions (production):

```bash
pip install "inguitive[redis]"
```

inguitive does **not** bundle an ASGI server. You run your app with
`uvicorn` (or any ASGI server you prefer):

```bash
pip install uvicorn[standard]
```

## Your first app — step by step

### 1. Create the app and the UI

```python
from fastapi import FastAPI
from inguitive import UI

app = FastAPI()
ui = UI(app, title="My App")
```

You construct the FastAPI app yourself, then pass it to `UI(app, ...)`.
`UI` attaches inguitive's UI layer: the `@ui.trigger_handler` surface,
`ui.page()`, session middleware, the `/_sse` endpoint, and the `/static`
mount. The optional `title`, `favicon`, and `head` parameters control the
browser tab and `<head>` content globally.

### 2. Define reactive state

```python
from inguitive import SessionState

counter = SessionState(0, "counter")
```

inguitive has two state scopes:

- **`SessionState`** — per-session. Each browser session gets its own isolated
  value; `set()` pushes updates only to that session's components.
- **`State`** — global. Shared across all sessions; `set()` broadcasts to
  every connected browser.

For a per-user counter, `SessionState` is the right choice. See
[State System](guide/state.md) for the full global-vs-session model.

### 3. Write a trigger handler

```python
@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)
```

Trigger handlers are plain Python functions (sync or async) decorated with
`@ui.trigger_handler`. inguitive registers an HTMX POST endpoint for each one
automatically. The handler returns `None`; the framework detects the state
mutation and generates the OOB swap response for you.

### 4. Build a component

```python
from inguitive import Div, Text, Button

def Counter():
    return Div(
        Text(
            lambda: f"Count: {counter.get()}",
            id="counter-label",
            listen_to=counter,
        ),
        Button("+1", trigger=increment),
    )
```

Key points:

- `text=lambda: ...` — any attribute can be a callable; it is re-evaluated on every render.
- `listen_to=counter` — pass the `State`/`SessionState` object itself (not a string). When `counter` changes, the component is re-rendered via OOB swap.
- `trigger=increment` — pass the handler callable itself (not a string). The component resolves the `hx-post` URL from the handler.
- `id="counter-label"` — required for OOB swaps; must match the element in the DOM.

### 5. Define a page

```python
@app.get("/")
def home():
    return ui.page(Counter())
```

Pages are plain FastAPI routes that return `ui.page(...)`. The component is
rendered and wrapped in a full HTML document (with Tailwind, HTMX, and the SSE
connection wired in automatically).

For dynamic URLs with parameters, see
[Routing and URL Parameters](guide/routing.md).

### 6. Run

```bash
uvicorn app:app --reload
```

Then open [http://localhost:8000](http://localhost:8000).

## Full counter example

```python
from fastapi import FastAPI
from inguitive import UI, SessionState, Div, Text, Button

app = FastAPI()
ui = UI(app, title="Counter")

counter = SessionState(0, "counter")


@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)


@ui.trigger_handler
def decrement():
    counter.set(counter.get() - 1)


def Counter():
    return Div(
        Button("-1", trigger=decrement),
        Text(
            lambda: str(counter.get()),
            id="counter-label",
            listen_to=counter,
            css="text-4xl font-bold mx-4",
        ),
        Button("+1", trigger=increment),
        css="flex items-center gap-4 p-8",
    )


@app.get("/")
def home():
    return ui.page(Counter())
```

## Next steps

- [Components](guide/components.md) — the full component library with recipes
- [State System](guide/state.md) — global `State` vs per-session `SessionState`
- [SSE Workflow](guide/sse.md) — server-initiated updates, global and session-scoped
- [Trigger Handlers](guide/trigger-handlers.md) — trigger args, async handlers, form data
- [Routing and URL Parameters](guide/routing.md) — dynamic URLs with FastAPI native path params
- [Session Backends](guide/session-backends.md) — scaling to production with Redis
