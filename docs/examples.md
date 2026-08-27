# Examples

All examples live in the `src/inguitive/examples/` directory of the
repository. Each one focuses on a single feature and can be run directly
with `uvicorn`. (There is no `examples` package on `sys.path`; use the
module path shown in each section.)

## Counter app

**File:** `src/inguitive/examples/counter_app.py`

Per-session reactive counter. Demonstrates:

- `State` with `get()` / `set()` and `listen_to` for automatic re-rendering
- Per-session isolation (two windows keep independent counts)
- Dynamic attributes via callables (`css` and `text` re-evaluated each render)
- The explicit-response form `return update_components(*state.listeners)`

```bash
uvicorn inguitive.examples.counter_app:app --reload
```

## Trigger arguments app

**File:** `src/inguitive/examples/trigger_args_app.py`

Passing data to a handler without a form. Demonstrates:

- `trigger_args` declared on a component and serialised onto the POST URL as query params
- `get_trigger_args()` returning a `dict[str, str]` in the handler
- One handler reused by several buttons that differ only in their `trigger_args`

```bash
uvicorn inguitive.examples.trigger_args_app:app --reload
```

## Auto-propagation app

**File:** `src/inguitive/examples/auto_propagation_app.py`

Letting the framework build the OOB response. Demonstrates:

- A trigger handler that mutates state and returns nothing
- The framework detecting changed `State` objects and auto-rendering their listeners as OOB swaps
- The no-return form as the counterpart to the explicit `update_components(...)` used elsewhere

```bash
uvicorn inguitive.examples.auto_propagation_app:app --reload
```

## Form app

**File:** `src/inguitive/examples/form_app.py`

Form components and `form_data`. Demonstrates:

- `Form` with `Input`, `Textarea`, `Select`, `Checkbox`, `Radio`, and `Label`
- Auto-set `name` attributes (matching the component `id`) so `form_data` keys line up
- A trigger handler receiving submitted values via the `form_data` parameter

```bash
uvicorn inguitive.examples.form_app:app --reload
```

## Validation app

**File:** `src/inguitive/examples/validation_app.py`

Declarative form validation. Demonstrates:

- `FormSchema` with typed, validated `field` declarations
- The `@validate_form` decorator and built-in validators
- `ValidationError` and the `raise_on_invalid` flag controlling raise-vs-pass-errors

```bash
uvicorn inguitive.examples.validation_app:app --reload
```

## Data table app

**File:** `src/inguitive/examples/data_table_app.py`

The `DataTable` component. Demonstrates:

- `data` as a callable returning `list[dict]`, re-evaluated on every render
- Dynamic `columns` via a callable (reorder / omit columns at runtime)
- Dictionary `css` for per-sub-element styling (`"table"`, `"header"`, `"row"`, `"cell"`)
- Multi-state `listen_to` so one table reacts to several `State` objects

```bash
uvicorn inguitive.examples.data_table_app:app --reload
```

## Icon app

**File:** `src/inguitive/examples/icon_app.py`

The `Icon` component. Demonstrates:

- `Markup`-safe SVG rendering (tags emitted verbatim, not entity-escaped)
- A dynamic icon via a callable that switches glyphs based on state
- Class rewriting so the `css` you pass applies to the SVG

```bash
uvicorn inguitive.examples.icon_app:app --reload
```

## Routing app

**File:** `src/inguitive/examples/routing_app.py`

Multi-page routing. Demonstrates:

- Multiple pages registered with `@app.page("/path")`
- `redirect()` for URL-level navigation (HTTP 302, address bar updates)
- `Link` for anchor-based navigation between routes

```bash
uvicorn inguitive.examples.routing_app:app --reload
```

## URL parameters app

**File:** `src/inguitive/examples/url_params_app.py`

Dynamic path segments `<name:type>`. Demonstrates:

- `int`, `str` (default), and `path` segment types with type coercion
- Automatic HTTP 400 on type mismatch, with no handler-level validation code
- The parsed, typed value passed to the page handler as a keyword argument

```bash
uvicorn inguitive.examples.url_params_app:app --reload
```

## SSE per-session app

**File:** `src/inguitive/examples/sse_session_app.py`

Server-Sent Events with per-user push. Demonstrates:

- A background task running inside `session_context` to write isolated state
- `push_update(session_id, *state.listeners)` re-rendering one user's component over their SSE stream
- An idempotency guard (live `asyncio.Task` in process memory) preventing duplicate loops

```bash
uvicorn inguitive.examples.sse_session_app:app --reload
```

## SSE global app

**File:** `src/inguitive/examples/sse_global_app.py`

Server-Sent Events as a global broadcast. Demonstrates:

- A startup task with no session bound, so `State.set()` takes the background-task branch
- Automatic OOB push to every connected tab whose components `listen_to` the state
- No `session_context`, `push_update`, or idempotency guard needed (single writer)

```bash
uvicorn inguitive.examples.sse_global_app:app --reload
```

## Session backends app

**File:** `src/inguitive/examples/session_backend_app.py`

Swapping session storage backends. Demonstrates:

- `MemoryBackend` (default, single-worker dev) vs `RedisBackend` (multi-worker prod)
- `set_session_backend()` chosen at startup from the `SESSION_BACKEND` env var
- Identical app code regardless of the backend in use

```bash
uvicorn inguitive.examples.session_backend_app:app --reload
SESSION_BACKEND=redis REDIS_URL=redis://localhost:6379 \
    uvicorn inguitive.examples.session_backend_app:app --reload
```

## nl2br app

**File:** `src/inguitive/examples/nl2br_app.py`

The `nl2br` utility. Demonstrates:

- Converting `\n` / `\r\n` / `\r` in a string to `<br>` tags for HTML line breaks
- Safe-by-default: HTML-special characters are escaped internally, so `nl2br(content)` is safe on untrusted input
- Returning `markupsafe.Markup` so the framework emits the result as HTML without re-escaping the `<br>` tags

```bash
uvicorn inguitive.examples.nl2br_app:app --reload
```

## Template app

**File:** `src/inguitive/examples/template_app.py`

`TemplateComponent` with Jinja2. Demonstrates:

- Rendering a Jinja2 template string as an inguitive component
- Callable context values resolved on every render (live `State` flowing in)
- Autoescaping on, matching the safety of the built-in components

```bash
uvicorn inguitive.examples.template_app:app --reload
```
