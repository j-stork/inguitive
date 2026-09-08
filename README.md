# inguitive

A pure Python web framework combining intuitive syntax with **HTMX** for partial page reloads and **Tailwind CSS** for styling.

Components automatically re-render when state changes, eliminating the need for manual DOM manipulation or JavaScript. It is designed for Python developers who want to build interactive web applications using only Python, without sacrificing the dynamic feel of modern SPAs.

## 3 Steps to a Running App

```bash
pip install inguitive
inguitive init
inguitive run
```

`inguitive init` scaffolds a ready-to-run `app.py` in the current directory. `inguitive run` serves it at `http://localhost:8000`.

## A Simple Example

Here's what a simple app might look like — a reactive counter that updates without a full page reload:

```python
from inguitive import Div, Button, Label, State, create_app

app = create_app(title="Counter")

counter = State(0, "counter")

@app.trigger_handler
def increment():
    counter.set(counter.get() + 1)

@app.page("/")
def index():
    return Div(
        Label(text=lambda: f"Count: {counter.get()}", id="counter-label", listen_to="counter"),
        Button("+1", trigger="increment"),
    )
```

## Features

- **Reactive State Management** — `State` propagates to all listening components automatically; no manual DOM updates or JavaScript
- **Component-Based** — composable UI components with clean Python syntax; all attributes can be static strings or callables
- **Trigger Handlers** — Python functions wired directly to HTMX POST actions; pass data from components to handlers via `trigger_args` and `get_trigger_args()`
- **Form Validation** — declarative `FormSchema` with type coercion and per-constraint messages
- **URL Routing** — dynamic path parameters with type validation (`<name:type>`)
- **Session Backends** — `MemoryBackend` for development, `RedisBackend` for production, with automatic per-user state isolation
- **CLI** — `inguitive init` and `inguitive run` to scaffold and serve
- **Type Safe** — full type hints throughout the codebase
- **Tailwind CSS** — first-class support for utility-first styling

## Documentation

For the full component reference, guides, and API docs, see [docs/index.md](docs/index.md).

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Contact:** [GitHub](https://github.com/j-strk) · [Issues](https://github.com/j-strk/inguitive/issues) · info@stork-software.de
