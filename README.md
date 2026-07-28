# INGUITIVE

A pure Python web framework combining intuitive syntax with **HTMX** for partial page reloads and **Tailwind CSS** for styling.

Unlike traditional request-response frameworks, INGUITIVE provides reactive state management where components automatically re-render when state changes, eliminating the need for manual DOM manipulation or JavaScript. It is designed for Python developers who want to build interactive web applications using only Python, without sacrificing the dynamic feel of modern SPAs.

## Features

- **Reactive State Management**: Components automatically re-render when state changes
- **HTMX Integration**: Out-of-band swaps for seamless partial page updates
- **Component-Based**: Composable UI components with clean Python syntax
- **Dynamic Attributes**: All component attributes can be static strings or callables
- **Trigger Arguments**: Pass data from components to handlers via `trigger_args` and `get_trigger_args()`
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

# Create FastAPI app
app, templates = create_app()  # templates is used in @app.page routes for Jinja2 rendering

# Create reactive state
counter_state = State(0, "counter_state")

# Define a trigger function
@app.trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)

# Define a component
def Counter():
    return Div(
        Label(text=lambda: f"Count: {counter_state.get()}", id="counter-label", listen_to="counter_state"),
        Button("+1", trigger="increment", css=BUTTON_PRIMARY_CSS),
    )

# Define a route function
@app.page("/")
def index():
    return Counter()
```

### Trigger Arguments

Pass data from a component to its handler using `trigger_args` on the component and `get_trigger_args()` in the handler:

```python
from inguitive import Button, Div, State, Text, create_app, get_trigger_args

app, templates = create_app()  # templates is used in @app.page routes for Jinja2 rendering
selected_state = State("none", "selected_state")

@app.trigger_handler
def select_item():
    item_id = get_trigger_args().get("id")
    selected_state.set(item_id)

@app.page("/")
def index():
    return Div(
        Button("Select A", trigger="select_item", trigger_args={"id": "a"}),
        Button("Select B", trigger="select_item", trigger_args={"id": "b"}),
        Text(lambda: f"Selected: {selected_state.get()}", listen_to="selected_state"),
    )
```

`trigger_args` are passed as URL query parameters; `get_trigger_args()` returns them as a `dict[str, str]` inside the handler.

## Component Reference

INGUITIVE provides a comprehensive set of components organized by category. All components support dynamic attributes via callables and can listen to state changes for automatic re-rendering.

### Base Components

| Component | Description | Key Parameters | Example |
|-----------|-------------|----------------|---------|
| **`Component`** | Base class for all components | `id`, `css`, `listen_to` | Custom component base |
| **`TemplateComponent`** | Render Jinja2 templates | `template`, context vars | Custom HTML with templating |

### Layout Components

| Component | Description | Key Parameters | Example |
|-----------|-------------|----------------|---------|
| **`Div`** | Container div element | `*children`, `id`, `css` | `Div(Button("Click"), css="flex gap-2")` |
| **`Text`** | Paragraph/text element | `text`, `id`, `css` | `Text("Hello", css="text-xl")` |
| **`Label`** | Form label element | `text`, `for_`, `id`, `css` | `Label("Name:", for_="name")` |

### Form Components

| Component | Description | Key Parameters | Example |
|-----------|-------------|----------------|---------|
| **`Form`** | Form container | `*children`, `action`, `method` | `Form(Input(...), Button(...))` |
| **`Input`** | Text input field | `type`, `value`, `placeholder`, `listen_to` | `Input(id="email", type="email")` |
| **`Textarea`** | Multi-line text input | `value`, `placeholder`, `rows` | `Textarea(id="bio", rows=5)` |
| **`Select`** | Dropdown select | `options`, `value`, `listen_to` | `Select(id="country", options=[...])` |
| **`Checkbox`** | Checkbox input | `checked`, `id`, `listen_to` | `Checkbox(id="agree", checked=True)` |
| **`Radio`** | Radio button input | `value`, `checked`, `name` | `Radio(id="male", name="gender")` |
| **`Button`** | Clickable button | `*children`, `trigger`, `css` | `Button("Click", trigger="action")` |

### Navigation Components

| Component | Description | Key Parameters | Example |
|-----------|-------------|----------------|---------|
| **`Link`** | Semantic navigation link | `*children`, `href`, `css` | `Link("Home", href="/")` |

### Data Display Components

| Component | Description | Key Parameters | Example |
|-----------|-------------|----------------|---------|
| **`DataTable`** | Tabular data display | `data`, `columns`, `css` | `DataTable(data=[{"name": "A"}])` |
| **`Icon`** | SVG icon component | `svg`, `css` | `Icon("<svg ...>...</svg>", css="w-6 h-6")` |

### Common Parameters (All Components)

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `str \| None` | HTML id attribute. Required for state listening and OOB updates |
| `css` | `str \| Callable[[], str] \| dict \| None` | Tailwind CSS classes. For DataTable, can be a dict with keys: `table`, `header`, `row`, `cell` |
| `listen_to` | `str \| list[str] \| None` | State name(s) to listen for changes. Triggers re-render when state updates |
| `trigger` | `str \| None` | Trigger name for HTMX POST actions (Button, Input, etc.) |
| `trigger_args` | `dict[str, str] \| None` | Query parameters to pass with trigger |

## Navigation & Actions

Use `Link` for traditional navigation (SEO, bookmarking, new-tab support) and `trigger` for partial page updates:

| | `Link(href="...")` | `trigger="..."` |
|---|---|---|
| Renders | `<a href="...">` | HTMX POST |
| URL changes | ✅ | ❌ |
| Open in new tab | ✅ | ❌ |

```python
from inguitive import Link, Button

# Traditional navigation
Link("Home", href="/")
Link("Documentation", href="/docs", css="text-blue-500")

# Partial updates
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
│       ├── htmx.py           # HTMX helpers
│       ├── fastapi.py       # FastAPI integration
│       └── svg.py           # SVG icon definitions
├── examples/
│   ├── counter_app.py        # Per-session counter with theme toggle
│   ├── todo_app.py           # CRUD with filtering and real-time count
│   ├── chat_app.py           # Real-time chat
│   ├── navigation_demo.py    # Link vs trigger patterns
│   ├── registration_form.py  # Form handling
│   └── data_table_app.py     # DataTable with sorting and filtering
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
app, templates = create_app()

# Or explicitly:
app, templates = create_app(session_backend=MemoryBackend())

# Production: Redis-backed sessions for scaling
app, templates = create_app(
    session_backend=RedisBackend(
        redis_url="redis://localhost:6379",
        ttl_seconds=3600  # Session timeout: 1 hour
    )
)
```

Requires `pip install redis` for RedisBackend.

### Session Lifetime and Expiry

INGUITIVE sessions are created automatically on first request and persist across page reloads. Each session has isolated component, state, and data registries.

**Session Creation:** A new session is created with a unique ID when a user first visits your application. The session ID is stored in a cookie.

**Session Persistence:** Sessions persist across page reloads and browser navigation within the same domain. The session cookie maintains the session ID, allowing the framework to restore the user's state.

**Session Expiry:**
- **MemoryBackend:** Sessions expire after `ttl_seconds` (default: 3600 = 1 hour) of inactivity. Expired sessions are automatically cleaned up every N requests (configurable via `session_cleanup_interval`).
- **RedisBackend:** Sessions are stored in Redis with a TTL. Redis automatically expires keys after the configured `ttl_seconds`, providing automatic cleanup.

**Differences Between Backends:**

| Aspect | MemoryBackend | RedisBackend |
|--------|---------------|--------------|
| Persistence | Lost on process restart | Survives process restarts |
| Multi-worker | Not supported (shared memory) | Supported (Redis as shared store) |
| Cleanup | Manual/Periodic via `cleanup_expired()` | Automatic via Redis TTL |
| Use Case | Development, testing | Production, scaling |

**Page Reload Behavior:** Session state is preserved across page reloads. Components listening to state will re-render with the current state values when the page loads.

## Production Deployment

Before deploying your INGUITIVE app to production, configure these security settings:

```python
from inguitive import create_app, RedisBackend

app, templates = create_app(
    session_backend=RedisBackend(redis_url="redis://localhost:6379"),
    session_cookie_secure=True,      # Cookies only over HTTPS
    session_cookie_httponly=True,    # Prevent JavaScript access (default)
    session_cookie_max_age=86400,    # 24-hour session timeout
)
```

**Checklist:**
- ✅ Use `RedisBackend` (not `MemoryBackend`) for persistence across workers
- ✅ Set `session_cookie_secure=True` when using HTTPS
- ✅ Verify `session_cookie_httponly=True` (enabled by default)
- ✅ Deploy with HTTPS (required for secure cookies)

## Running the Demo

```bash
# From the repository root
uvicorn examples.counter_app:app --reload

# Then open http://localhost:8000
```

## License

MIT License - see [LICENSE](LICENSE) for details.
