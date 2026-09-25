# Examples

All examples live in the `examples/` directory at the repository root. Each
one focuses on a single feature and can be run directly with `uvicorn` from
the repo root.

All examples are limited to the essentials: no custom component helpers,
minimal CSS, and trigger handlers use auto-propagation — state is mutated
via `State.set()` / `SessionState.set()` and the framework renders the
listeners automatically. The explicit `return update_components(...)` form
is noted in a comment wherever auto-propagation is used.

## Manual global counter app

**File:** `examples/counter_global_app.py`

A global counter incremented by a button. Demonstrates:

- `State` with `get()` / `set()` and `listen_to` for automatic re-rendering
- Global scope: the same value is shared across all sessions (browser windows)
- Dynamic attributes via callables (the label re-evaluated each render)
- Auto-propagation: the handler mutates state and returns nothing

```bash
uvicorn examples.counter_global_app:app --reload
```

## Manual session counter app

**File:** `examples/counter_session_app.py`

A per-session counter incremented by a button. Mirrors the global counter
app as closely as possible, but uses `SessionState`. Demonstrates:

- `SessionState` instead of `State` — the only structural difference
- Per-session isolation (two windows keep independent counts)
- Auto-propagation, as in the global counter app

```bash
uvicorn examples.counter_session_app:app --reload
```

## Global SSE counter app

**File:** `examples/sse_global_app.py`

Server-Sent Events as a global broadcast. Demonstrates:

- A startup task with no session bound, so `State.set()` takes the background-task branch
- Automatic OOB push to every connected tab whose components `listen_to` the state
- No `session_context` or idempotency guard needed (single writer)

```bash
uvicorn examples.sse_global_app:app --reload
```

## Session SSE counter app

**File:** `examples/sse_session_app.py`

Server-Sent Events with per-user push. Demonstrates:

- A per-session background task started from a trigger handler via `asyncio.create_task` (inherits the bound session)
- `SessionState.set()` auto-pushing OOB HTML to only this session's open SSE connections
- `session_active()` as the loop's termination condition
- An idempotency guard (live `asyncio.Task` in process memory) preventing duplicate loops

```bash
uvicorn examples.sse_session_app:app --reload
```

## Components app

**File:** `examples/components_app.py`

A static showcase of all available components in a two-column grid: each
component on the left, the HTML tag it renders to on the right. No
reactivity — a visual reference for the component library. Demonstrates:

- Every public component: `Div`, `Text`, `Header`, `Button`, `Anchor`,
  `Image`, `Icon`, `Label`, `Input`, `Textarea`, `Select`, `Checkbox`,
  `Radio`, `Form`, `DataTable`, and `TemplateComponent`
- The rendered HTML tag for each component

```bash
uvicorn examples.components_app:app --reload
```

## nl2br app

**File:** `examples/nl2br_app.py`

The `nl2br` utility. Demonstrates:

- Converting `\n` / `\r\n` / `\r` in a string to `<br>` tags for HTML line breaks
- A fixed multi-line string displayed once without and once with `nl2br()`
- Returning `markupsafe.Markup` so the framework emits the result as HTML without re-escaping the `<br>` tags

```bash
uvicorn examples.nl2br_app:app --reload
```

## Trigger arguments app

**File:** `examples/trigger_args_app.py`

Passing data to a handler without a form. Demonstrates:

- `trigger_args` declared on a component and serialised onto the POST URL as query params
- `get_trigger_args()` returning a `dict[str, str]` in the handler
- One handler reused by several buttons that differ only in their `trigger_args`
- Auto-propagation: the handler mutates state and returns nothing

```bash
uvicorn examples.trigger_args_app:app --reload
```
