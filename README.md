<p align="center">
  <img src="src/inguitive/static/inguitive_logo_600.png" alt="inguitive" width="200">
</p>

# inguitive

A pure Python UI layer for **FastAPI** — an alternative to template engines like Jinja2. Compose pages from Python components instead of templates, with reactive state and SSE-driven partial updates via **HTMX**. Styled with **Tailwind CSS**.

Components automatically re-render when state changes, eliminating the need for manual DOM manipulation or JavaScript. inguitive complements FastAPI rather than replacing it: routing, path parameters, form handling, and lifespan events stay FastAPI's job; inguitive owns the UI.

## Quick Start

```bash
pip install inguitive
```

```python
from fastapi import FastAPI
from inguitive import UI, Div, Button, Text, SessionState

app = FastAPI()
ui = UI(app, title="Counter")    # attaches middleware, the /_sse route, and /static

counter = SessionState(0, "counter")

@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)    # listening components re-render automatically

@app.get("/")
def home():
    return ui.page(
        Div(
            Text(lambda: f"Count: {counter.get()}", listen_to=counter),
            Button("+1", trigger=increment),
        ),
    )
```

Run it with `uvicorn app:app --reload` and open `http://localhost:8000`.

## Features

- **Components** — composable UI primitives (`Div`, `Text`, `Button`, ...). All attributes can be static strings or callables.
- **State system** — `State` (global, shared across sessions) and `SessionState` (per-session). `state.set()` triggers automatic partial page updates via HTMX out-of-band (OOB) swaps to components that `listen_to` that state.
- **SSE workflow** — server-initiated updates, both global (broadcast to all sessions) and session-scoped (pushed to one session's open connections).
- **Trigger handlers** — Python functions wired to HTMX POST actions via `@ui.trigger_handler`. `trigger=increment` on a component resolves to the handler's URL; `listen_to=counter` resolves to the state object.
- **`ui.page()`** — renders the full HTML document shell (`<!DOCTYPE html>`, `<head>`, HTMX/Tailwind CDN scripts, the hidden SSE auto-connect div). You compose only the body content with components.
- **Session backends** — `MemoryBackend` for development (default), `RedisBackend` for production via the optional `inguitive[redis]` extra.

## Documentation

For the full component reference, guides, and API docs, see [docs/index.md](docs/index.md).

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Contact:** [GitHub](https://github.com/j-strk) · [Issues](https://github.com/j-strk/inguitive/issues) · info@stork-software.de
