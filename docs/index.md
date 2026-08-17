# inguitive

**A pure Python reactive web framework — HTMX + Tailwind without JavaScript.**

inguitive lets Python developers build interactive web applications using only Python.
Components automatically re-render when state changes via HTMX out-of-band swaps.
Each browser session has isolated state — no global mutable variables, no JavaScript required.

```python
from inguitive import Div, Button, Label, State, create_app
from inguitive.css import BUTTON_PRIMARY_CSS

app = create_app(title="Counter")
counter = State(0, "counter")

@app.trigger_handler
def increment():
    counter.set(counter.get() + 1)

@app.page("/")
def index():
    return Div(
        Label(text=lambda: f"Count: {counter.get()}", id="counter-label", listen_to="counter"),
        Button("+1", trigger="increment", css=BUTTON_PRIMARY_CSS),
    )
```

## Why inguitive?

| | Traditional Python web | inguitive |
|---|---|---|
| Interactivity | Requires JavaScript | Pure Python |
| State updates | Full page reload or custom JS | HTMX out-of-band swaps |
| Per-user state | Manual session plumbing | Built-in `State` + session isolation |
| Form validation | Roll your own | Declarative `FormSchema` |

## Features

- **Reactive state** — `State` propagates to all listening components automatically
- **Component model** — composable, callable-attribute UI components
- **Trigger handlers** — Python functions wired directly to HTMX POST actions
- **Form validation** — declarative schemas with type coercion and per-constraint messages
- **Session backends** — `MemoryBackend` for development, `RedisBackend` for production
- **CLI** — `inguitive init` and `inguitive run` to scaffold and serve

## Quick links

- [Getting Started](getting-started.md) — install and run your first app in five minutes
- [Component Reference](guide/components.md) — every built-in component with examples
- [Form Validation](guide/form-validation.md) — the `FormSchema` / `validate_form` API
- [API Reference](api/index.md) — full auto-generated reference from source docstrings
