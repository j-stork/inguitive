# INGUITIVE

A pure Python web framework combining intuitive syntax with **HTMX** for partial page reloads and **Tailwind CSS** for styling.

## Features

- **Reactive State Management**: Components automatically re-render when state changes
- **HTMX Integration**: Out-of-band swaps for seamless partial page updates
- **Component-Based**: Composable UI components with clean Python syntax
- **Dynamic Attributes**: All component attributes can be static strings or callables
- **Type Safe**: Full type hints throughout the codebase
- **Tailwind CSS**: First-class support for utility-first styling

## Quick Start

### Installation

```bash
pip install inguitive
```

### Basic Example

```python
from inguitive import Div, Button, Label, State, create_app
from inguitive.css import BUTTON_PRIMARY_CSS
from inguitive.htmx import update_components

# Create reactive state
counter_state = State(0, "counter_state")

# Define a component
def Counter():
    return Div(
        Label(text=lambda: f"Count: {counter_state.get()}", id="counter-label", listen_to="counter_state"),
        Button("+1", trigger="increment", cls=BUTTON_PRIMARY_CSS),
    )

# Create FastAPI app
app = create_app()

@app.post("/increment")
def increment():
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)
```

## When to Use: Navigation & Actions

### Decision Guide

| Component/Parameter | Renders | Use When | URL Changes | Native Link Behavior |
|---------------------|---------|----------|-------------|---------------------|
| **`A(href="...")`** | `<a href="...">` | Traditional links, SEO, accessibility | ✅ Yes | ✅ Full support |
| **`navigate="/..."`** | `hx-get`, `hx-target="body"` | SPA-style navigation between related components | ❌ No (add `hx-push-url="true"` to enable) | ❌ No |
| **`redirect="/..."`** | `hx-redirect` | Immediate full-page redirect | ✅ Yes | ❌ No |
| **`trigger="..."`** | `hx-post`, `hx-target="#hx-target"` | Form submissions, partial updates | ❌ No | ❌ No |

### Decision Tree

```
Is this a traditional link that users might:
   │
   ├── want to open in a new tab? ──YES──► Use A(href="...")
   │
   ├── want to bookmark/share? ───────YES──► Use A(href="...")
   │
   └── want SEO to find? ──────────────YES──► Use A(href="...")
           │
           NO
           │
    Is this navigation between related components
    (tabs, modals, SPA views)? ──YES──► Use navigate="/..."
           │
           NO
           │
    Does this need an immediate full redirect? ──YES──► Use redirect="/..."
           │
           NO
           │
    Is this a form action or partial update? ──YES──► Use trigger="..."
```

### Common Patterns

```python
from inguitive import A, Button, Text, Div

# Traditional navigation (SEO, accessibility, bookmarking)
A("Home", href="/")
A("Documentation", href="/docs", cls="text-blue-500")

# SPA-style view switching (tabs, modals, stacked components)
# Example: Toggle between Login, Register, Logout forms
Div(
    Text("Login", navigate="/auth?mode=login", cls="cursor-pointer"),
    Text(" | "),
    Text("Register", navigate="/auth?mode=register", cls="cursor-pointer"),
)

# Immediate redirect (logout, etc.)
Button("Logout", redirect="/logout")

# Partial updates (forms, actions that update specific elements)
Button("Save", trigger="save_form")
Button("Like", trigger="like_post", trigger_args={"id": "123"})
```

## Project Structure

```
.
├── src/
│   └── inguitive/
│       ├── __init__.py      # Public API
│       ├── components.py    # Component classes
│       ├── state.py         # Reactive state
│       ├── hx.py             # HTMX helpers
│       ├── fastapi.py       # FastAPI integration
│       └── svg.py           # SVG icon definitions
├── examples/
│   └── counter_app.py       # Demo application
├── tests/
│   └── test_*.py           # Test files
├── pyproject.toml           # Build configuration
└── README.md
```

## Session Backends

INGUITIVE uses session-scoped registries to isolate user state. Choose a backend based on your deployment needs:

| Backend | Use When | Persistence | Multi-Worker |
|---------|----------|-------------|--------------|
| **`MemoryBackend`** | Development, single worker | ❌ No (lost on restart) | ❌ No |
| **`RedisBackend`** | Production, multiple workers | ✅ Yes | ✅ Yes |

**MemoryBackend** (default) stores sessions in RAM - perfect for development. **RedisBackend** stores sessions in Redis for production deployments with multiple workers or persistent sessions.

```python
from inguitive import create_app, MemoryBackend, RedisBackend

# Development: In-memory sessions (default, no config needed)
app = create_app()

# Or explicitly:
app = create_app(session_backend=MemoryBackend())

# Production: Redis-backed sessions for scaling
app = create_app(
    session_backend=RedisBackend(
        redis_url="redis://localhost:6379",
        ttl_seconds=3600  # Session timeout: 1 hour
    )
)
```

Requires `pip install redis` for RedisBackend.

## Running the Demo

```bash
# From the repository root
uvicorn examples.counter_app:app --reload

# Then open http://localhost:8000
```

## License

MIT License - see [LICENSE](LICENSE) for details.
