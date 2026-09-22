# inguitive

**A pure Python UI layer for FastAPI — HTMX + Tailwind without JavaScript.**

inguitive lets Python developers build interactive web applications using only Python.
Pages are composed from Python components, not templates. Components automatically
re-render when state changes via HTMX out-of-band swaps. State is either global (shared
across all sessions) or per-session (isolated per browser) — no global mutable variables,
no JavaScript required.

inguitive complements FastAPI rather than replacing it: routing, path parameters, form
handling, and lifespan events stay FastAPI's job; inguitive owns the UI.

```python
from fastapi import FastAPI
from inguitive import UI, SessionState, Div, Text, Button

app = FastAPI()
ui = UI(app, title="Counter")

counter = SessionState(0, "counter")


@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)    # listening components update automatically


@app.get("/")
def home():
    return ui.page(
        Div(
            Text(lambda: f"Count: {counter.get()}", id="counter-label", listen_to=counter),
            Button("+1", trigger=increment),
        ),
    )
```

## Why inguitive?

| | Traditional Python web | inguitive |
|---|---|---|
| Interactivity | Requires JavaScript | Pure Python |
| State updates | Full page reload or custom JS | HTMX out-of-band swaps |
| Per-user state | Manual session plumbing | Built-in `SessionState` (per-session) + `State` (global) |
| Server push | WebSockets or polling | SSE with automatic OOB swaps |
| Routing | Framework-specific wrappers | Native FastAPI routes |

## Features

- **Component model** — composable, callable-attribute UI components (`Div`, `Text`, `Button`, …)
- **Reactive state** — `State` (global) and `SessionState` (per-session); `.set()` propagates to listening components automatically
- **Trigger handlers** — Python callables wired directly to HTMX POST actions via `@ui.trigger_handler`
- **SSE workflow** — server-initiated updates, both global (broadcast to all sessions) and session-scoped (pushed to one session)
- **Session backends** — `MemoryBackend` for development, `RedisBackend` for production (via the `inguitive[redis]` extra)
- **FastAPI-native routing** — path parameters, form handling, and dependencies used directly

## Quick links

- [Getting Started](getting-started.md) — install and run your first app in five minutes
- [Components](guide/components.md) — every built-in component with copy-paste recipes
- [State System](guide/state.md) — global `State` vs per-session `SessionState`
- [SSE Workflow](guide/sse.md) — server-initiated pushes, global and session-scoped
- [API Reference](api/index.md) — full auto-generated reference from source docstrings
