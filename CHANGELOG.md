# inguitive Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-09-21

A major realignment. inguitive is now a **UI layer for FastAPI** — an alternative to template engines like Jinja2 — rather than a standalone web framework. The feature set is reduced to three pillars: **Components**, the **State system** (`State` + `SessionState`), and the **SSE workflow** (global broadcast + session-scoped push). Everything outside these pillars is left to FastAPI.

This is a breaking release: the `create_app()` factory, `@app.page` decorator, CLI, form validation, path-param engine, Jinja2 template loader, and `push_update` are all removed. See the migration notes below.

### Changed (breaking)

- **`UI(app, ...)` replaces `create_app()`.** The user owns the FastAPI app and constructs it themselves (`app = FastAPI(); ui = UI(app, ...)`). `UI()` attaches the UI layer synchronously: `@ui.trigger_handler`, `ui.page()`, session middleware (auto-added by default; opt out via `configure_session_middleware=False`), the `/_sse` endpoint, and the `/static` mount. FastAPI's constructor surface (lifespan, docs URLs, OpenAPI metadata) stays fully in the user's hands.
- **`ui.page(component, ...)` replaces `@app.page`.** Pages are plain `@app.get(...)` routes that return `ui.page(...)`. The method renders the component and wraps it in a full HTML document shell (`<!DOCTYPE html>`, `<head>` with metas, HTMX/Tailwind CDN scripts, the hidden `#hx-target` div) — no Jinja2 template, no `base.html`. Optional per-page overrides: `title`, `favicon`, `head`, `replace_global_head`.
- **`State` is global; `SessionState` is per-session.** Scope is declared at construction time, not inferred from context. `State.set()` broadcasts OOB updates to every session. `SessionState.set()` pushes only to the current session. This replaces the previous implicit-scope model and removes a class of "which session did I just write to?" bugs.
- **`.set()` returns `None`; propagation is automatic.** The framework tracks state mutations during a trigger handler's execution and, at handler exit, automatically renders OOB updates for the listening components. The handler does not return OOB HTML.
- **`listen_to` accepts `State`/`SessionState` objects** (or a list of them), not strings. The framework registers the component as a listener on the state object directly — no name lookup.
- **`trigger` accepts a callable** — the decorated trigger handler function. The `@ui.trigger_handler` decorator attaches the trigger's route URL to the function object, so `trigger=increment` resolves to the right `hx-post` URL without string lookups.
- **`Link` renamed to `Anchor`.** The component that renders `<a>` is now `Anchor`, freeing the `Link` name for a future `<link>` component.
- **Form data is opt-in, not auto-injected.** The magic `form_data: dict` parameter injection is removed. Handlers that want form data declare a `request: Request` parameter and call `get_form_data(request)` — a new explicit helper. All form-using handlers are now async.
- **`RedisBackend` moved to an optional extra.** `pip install inguitive[redis]`, then `from inguitive.backends.redis import RedisBackend`. `MemoryBackend` is the default. `RedisBackend` is no longer exported from `inguitive.__init__`.

### Added

- **`session_active()`** — predicate returning `True` while the current session has at least one open SSE connection. Intended as the loop condition for session-scoped background tasks: `while session_active(): ...` terminates the task cleanly when the user closes every tab. The explicit, less-magic alternative to framework-injected task cancellation.
- **`get_form_data(request: Request) -> dict[str, str]`** — explicit helper replacing the removed `form_data` auto-injection. Handlers declare `request: Request` and call `await get_form_data(request)`.
- **Global `State.set()` SSE broadcast.** `State.set()` from any context (trigger handler or background task) now auto-pushes OOB HTML to every connected session's SSE queues. `SessionState.set()` from a background task (via `asyncio.create_task` context copy or `session_context`) auto-pushes to only that session's queues. No explicit push call needed.
- **`configure_session_middleware` flag on `UI`.** `True` (default) auto-adds `SessionMiddleware` in `UI.__init__`. `False` opts out — the user adds it themselves. A startup check and request-time backstop raise a loud, actionable error if the middleware is missing.
- **Document shell rendered in Python.** `ui.page()` composes `<!DOCTYPE html>`, `<head>`, CDN scripts, and the SSE auto-connect div as Python strings — no Jinja2, no `base.html`, no `error.html`.

### Removed

- **`create_app()`, `run_app()`, `redirect()`** — replaced by `UI(app, ...)` and FastAPI's own utilities.
- **`@app.page` decorator** — replaced by `@app.get(...)` + `ui.page(...)`.
- **CLI (`inguitive init`, `inguitive run`)** — removed entirely, along with the `[project.scripts]` entry in `pyproject.toml`.
- **Form validation layer** — `FormSchema`, `field()`, `validate_form()`, all validators, `ValidationError`. Users use FastAPI's own validation or write their own.
- **Path-parameter conversion engine** — `_PATH_PARAM_CONVERTERS`, `_convert_path_param`, `_parse_path_pattern`. Users use FastAPI's native path parameters.
- **Jinja2 template loader and templates** — `base.html`, `error.html`, `Jinja2Templates`, `ChoiceLoader`, the `templates` env. `TemplateComponent` keeps the `jinja2` dependency (it renders Jinja2 templates as a component).
- **`push_update()`** — redundant with the auto-push path: `State.set()` broadcasts globally; `SessionState.set()` auto-pushes to the current session. Removed from `fastapi.py`, `__init__.py`, tests, docs, and the multi-worker broker recipe (rewritten as a build-it-yourself recipe on `update_components` + `_get_sse_queues`).
- **`push_update`, `create_app`, `run_app`, `redirect`, `Link`, `RedisBackend`** removed from `inguitive.__init__` exports.
- **`Session`** no longer re-exported from the top-level package — advanced users import it from `inguitive.session`.

### Kept

- **`session_context` and `get_session_id`** — needed to bind a session by ID outside a request (e.g. a startup/webhook task targeting a specific user's `SessionState`).
- **`DataTable`, `TemplateComponent`, `Icon`, `Label`** — kept for their respective use cases (quick data visualization, complex HTML escape hatch, SVG rendering, form semantics).
- **`MemoryBackend`, `SessionBackend`, `set_session_backend`, `get_session_backend`** — core session infrastructure.
- **`get_trigger_args`, `update_components`, `nl2br`** — unchanged.

### Internal

- `uvicorn[standard]` moved from a hard dependency to the `dev` extra — the library never imports it at module load; the server choice is the user's.
- Package description and keywords reframed from "web framework" to "UI layer for FastAPI".
- SSE guide (`docs/guide/sse.md`) rewritten to the new API. Session backends guide broker recipe rewritten without `push_update`.
- All 13 surviving examples verified to use the `UI(app, ...)` pattern. `sse_session_app.py` rewritten to `SessionState` + `session_active()` + `asyncio.create_task`.
- 336 tests passing, 1 skipped.

---

## [1.0.1] - 2026-09-11

### Fixed

- **SSE generator leaked orphaned tasks on client disconnect**: the `_event_generator` in the `/_sse` route cancelled the disconnect and queue tasks but never awaited them, leaving them pending. Python then destroyed them mid-flight and logged "Task was destroyed but it is pending". Both tasks are now cancelled and awaited in the `finally` block so their cancellations settle before the generator returns.
- **SSE connections exhausted browser connection limit during rapid navigation**: every page opened a `/_sse` connection via `base.html`, but the connection was never closed on navigation — the server only detected disconnects via a 0.5s poll. Zombie SSE connections accumulated and exhausted the browser's 6-connection HTTP/1.1 limit, blocking page loads from the 6th transition onward. Added a `pagehide` handler that triggers the SSE extension's own `htmx:beforeCleanupElement` event on `#hx-target`, closing the `EventSource` immediately when the browser navigates away.

---

## [1.0.0] - 2026-09-10

### Changed (breaking)

- **`nl2br()` is now safe-by-default**: escapes HTML internally and returns `markupsafe.Markup` instead of `str`. HTML in the input is escaped rather than preserved. Callers no longer need to wrap with `Markup(nl2br(str(escape(content))))`; pre-escaped content can be wrapped in `Markup` by the caller.
- **`validate_form` parameter renamed**: `handle_errors` → `raise_on_invalid`. Semantics unchanged — `True` (default) raises `ValidationError`, `False` injects the errors dict into the handler.

### Added

- **`session_context`**: async context manager for per-session background tasks. Binds a session outside an HTTP request so `State.set()` writes to that session's isolated data instead of broadcasting globally. Exported from `inguitive.__init__`.
- **`push_update` in-context session reuse**: when called inside a `session_context` targeting the bound session, `push_update` reuses the in-context session instead of reloading from the backend (avoids stale reads on serializing backends).
- **Custom static file serving**: `create_app()` now checks `CWD/static/` first, then package `static/`, so users can serve their own files (SVG, PNG, etc.).
- **`inguitive init` updated**: scaffolded `app.py`/`css.py`/`svg.py` content revised; now prompts to create `llms-inguitive.md` for LLM indexing.

### Fixed

- **`Icon.render()` dropped the component id**: broke HTMX OOB swaps (silent no-op because the DOM had no matching element). Id is now set on the root `<svg>`.
- **`TemplateComponent.render()` dropped the component id**: same OOB breakage. Rendered template is now wrapped in `<div {attrs}>` to match `update()`.
- **`static_files_app` didn't transmit responses**: Starlette `Response` objects were returned but never awaited; also fixed wrong path resolution under `Mount` (doubled `/static` segment).

### Internal

- **Decorators hoisted to module level**: `@app.page` and `@app.trigger_handler` extracted from nested closures to module-level functions (bound via `functools.partial`); user code unchanged. Makes them visible to `gather_package_documentation()` for `llms-inguitive.md`.
- **`gather_package_documentation()` refactored**: now uses AST instead of line scanning; improved docstring extraction and output formatting.
- **mypy fixes**: `Traversable` type errors in `fastapi.py`, AST return type narrowing in `_top_level_definitions`.

### Documentation

- SSE guide expanded with multi-worker deployment recipes (sticky sessions, broker pattern) and a session-scoped background task recipe using `session_context`.
- 14 focused example apps added/rewritten; obsolete example apps deleted.
- README shortened and restructured with logo, 3-step quick start, and lean features list.

---

## [0.9.0] - 2026-08-25

### Added

- **Image component**: Renders `<img>` tags for displaying images. Supports `src`, `alt`, `css`, and all standard HTML image attributes (width, height, loading, etc.). Supports dynamic values via callables and HTMX out-of-band updates.
- **Icon.update() method**: Added `update()` method to Icon component for HTMX out-of-band update support, consistent with all other components.

---

## [0.8.0] - 2026-08-24

### Added

- **Header component**: Renders `<h1>` through `<h6>` headings with configurable `level` parameter (default: 1). Supports dynamic text, CSS styling, and HTMX out-of-band updates.

---

## [0.7.0] - 2026-08-21

### Added

- **URL path parameters for @app.page decorator**: Dynamic URL segments with type validation using `<name:type>` syntax
- Supported types: `str`, `int`, `float`, `bool`, `path`, `uuid` with automatic conversion and validation
- Type validation with HTTP 400 errors for invalid input (e.g., `/user/abc` when expecting `int`)
- Boolean type accepts: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` (case-insensitive)
- `path` type preserves slashes in URL segments (e.g., `/files/a/b/c.txt`)
- `uuid` type validates and converts to UUID objects
- Multiple path parameters per route (e.g., `/user/<user_id:int>/post/<post_id:int>`)
- Default type is `str` when no type is specified
- Unknown type names are treated as `str`
- Path parameters work alongside `request` and `form_data` parameters
- Reserved parameter names `request` and `form_data` are rejected with clear error messages
- Comprehensive documentation in `docs/guide/routing.md`
- 20 new tests covering all type conversions, validation, and edge cases

### Internal

- `src/inguitive/fastapi.py`: Added `_PATH_PARAM_CONVERTERS` registry, `_parse_path_pattern()` for syntax conversion, `_convert_path_param()` for type conversion and validation, updated `_register_page_route()` to handle path parameters
- Added validation to prevent reserved names (`request`, `form_data`) as path parameter names
- Added validation to reject type names starting with underscore

---

## [0.6.0] - 2026-08-17

### Added

- **SSE server-push support**: the server can now push component updates to any connected browser tab without a user interaction
- `push_update(session_id, *component_ids)` — explicit per-session push from any async context; re-renders the named components as OOB swaps and streams the HTML to the client's SSE connection
- `State.set()` from outside a request context (background tasks, startup handlers) now broadcasts the new value as a global and automatically pushes OOB HTML to every connected session whose components listen to that state — no extra API needed
- `State.get()` from outside a request context returns the last broadcast value (or the initial value if none has been set), with per-session values still taking precedence inside a request
- `GET /_sse` streaming endpoint registered by `create_app()`; each page opens this connection automatically via the `hx-ext="sse"` attribute on the hidden `#hx-target` div
- HTMX SSE extension script added to `base.html`
- 21 new tests covering the SSE registry, global state semantics, `_push_sse_for_state`, `push_update`, and the `/_sse` route

### Internal

- `src/inguitive/session.py`: `_sse_connections` registry dict; `_register_sse_connection`, `_unregister_sse_connection`, `_get_sse_queue` helpers
- `src/inguitive/state.py`: `_global_state_values` broadcast dict; `_schedule_sse_push`, `_push_sse_for_state` for async push fanout; updated `State.get` and `State.set` for background-task semantics
- `src/inguitive/fastapi.py`: `push_update` coroutine; `/_sse` route with disconnect-aware async generator (30 s heartbeat, 0.5 s disconnect poll)
- `push_update` exported from `inguitive.__init__`

---

## [0.5.0] - 2026-08-17

### Added

- Form validation layer: `FormSchema`, `field()`, and `validate_form()` decorator for declarative type coercion, required-field enforcement, and per-constraint error messages in trigger handlers
- Built-in validators: `RequiredValidator`, `MinLengthValidator`, `MaxLengthValidator`, `MinValueValidator`, `MaxValueValidator`, `RegexValidator`
- `CustomValidator` for arbitrary per-field validation logic
- `ValidationError` for raising cross-field errors inside `FormSchema.validate()`
- `validate_form(SchemaClass)` decorator integrates directly with `@app.trigger_handler`; injects the validated schema as a typed parameter and returns structured errors on failure
- Full inheritance support for `FormSchema` subclasses, including correct MRO-ordered field resolution for multiple inheritance
- 95 unit tests covering all validators, coercion, inheritance, cross-field validation, and decorator integration

---

## [0.4.1] - 2026-07-27

### Fixed

- Fixed `inguitive run` failing to import the app module on all platforms by inserting CWD into `sys.path` and `PYTHONPATH` before starting uvicorn

---

## [0.4.0] - 2026-07-27

### Added

- Command-line interface (`inguitive init`, `inguitive run`, `inguitive --version`)
- `inguitive init` scaffolds a ready-to-run `app.py` in the current directory
- `inguitive run` starts uvicorn with auto-reload; supports `--host`, `--port`, and `--no-reload` flags
- Rich-styled error panels for all CLI error output

---

## [0.3.0] - 2026-07-24

### Added

- Favicon parameter for `create_app()` to customize application favicon
- Default favicon SVG included with the package
- Warning message when static files cannot be mounted
- Test coverage for static favicon endpoint

### Changed

- Improved static file mounting error handling
- Code cleanup: consolidated imports, removed duplicates

### Fixed

- Fixed favicon link rendering (removed hardcoded type attribute)
- Fixed favicon type annotation (removed incorrect Path type)
- Fixed static mounting edge cases and RuntimeError handling

---

## [0.2.0] - 2026-07-23

### Added

- Customizable page titles via `create_app(title="...")` for app-level defaults
- Per-page title override via `@app.page("/path", title="Page Title")` decorator
- Proper title fallback chain: page title → app title → default "inguitive"
- Comprehensive test suite for title functionality (7 new tests in `TestPageTitles`)

### Changed

- Updated base.html template to use `{{ title }}` variable instead of hardcoded title
- Updated `_PageDecorator` type alias to include title parameter
- Added `# type: ignore[attr-defined]` annotations to suppress Pylance warnings for private function imports

### Fixed

- No bug fixes in this release

---

## [0.1.3] - 2026-07-22

### Added

- Bundled templates with inguitive package for out-of-the-box functionality
- Updated Replit configuration

### Changed

- Changed HTML language attribute from 'de' to 'en' in base template

### Removed

- Removed redundant root-level `templates/` directory (templates are now bundled with the package)

### Fixed

- Fixed `nl2br()` to handle Windows (CRLF) and old Mac (CR) line endings
- Fixed mypy type error for mixed loader types in fastapi.py
- Applied ruff formatting fixes

---

## [0.1.2] - 2026-07-21

### Added

- Bumped version to 0.1.2 for PyPI re-upload

---

## [0.1.1] - 2026-07-20

### Added

- Created `llms.txt` and `llms-full.txt` files based on the proposed standards from https://llmstxt.org/

---

## [0.1.0] - 2026-07-17

### Added

#### Core Features

**Reactive State Management**
- `State` class for managing application state
- Automatic component re-rendering when state changes
- Listener tracking via `listen_to` parameter
- Auto-propagation of state updates to listening components
- Context-local mutation tracking

**HTMX Integration**
- Native HTMX attribute support on all components
- Out-of-band (OOB) swap functionality via `update_components()`
- Trigger handlers with `@app.trigger_handler` decorator
- Form data injection in trigger handlers
- Async trigger handler support
- Trigger argument context via `get_trigger_args()`

**Component System**
- 16 built-in components: `Component`, `Div`, `Button`, `Label`, `Icon`, `Input`, `Textarea`, `Select`, `Checkbox`, `Radio`, `Form`, `Text`, `Link`, `Header`, `TemplateComponent`, `DataTable`
- All component attributes support dynamic values via callables
- Composable UI components with clean Python syntax
- Tailwind CSS first-class support for all components
- `DataTable` supports dict-based CSS for per-element styling (`table`, `header`, `row`, `cell` keys)

**Session Management**
- Per-session state isolation (each browser has independent state)
- `MemoryBackend` for development (in-memory storage)
- `RedisBackend` for production (Redis-based persistence)
- Session expiry and automatic memory cleanup
- Session ID management utilities

**FastAPI Integration**
- `InguitiveApp` Protocol for type-safe access to `@app.page` and `@app.trigger_handler` decorators
- `create_app()` factory for easy app creation
- `@app.page` decorator for page routes
- `@app.trigger_handler` decorator for trigger handlers
- `redirect()` and `run_app()` utilities

**Styling**
- First-class Tailwind CSS support
- Predefined CSS constants (`BUTTON_BASE_CSS`, `BUTTON_PRIMARY_CSS`, `BUTTON_SECONDARY_CSS`)
- Dynamic CSS via callables for all components
- Per-component CSS customization

#### Example Applications
- `counter_app.py`: Per-session isolation with counter and theme toggle
- `todo_app.py`: CRUD operations with filtering and real-time count
- `chat_app.py`: Real-time chat demonstration
- `navigation_demo.py`: Navigation patterns (Link vs trigger)
- `registration_form.py`: Form handling demonstration
- `data_table_app.py`: Data table with sorting and filtering

#### Test Coverage
- 11 test files covering all major functionality
- Tests for async handlers, components, decorators
- Tests for form data injection, session backends, state isolation
- Tests for trigger arguments

### Fixed
- Fixed `dynamic()` evaluating at call time instead of render time
- Fixed `RedisBackend` serialization of component registry
- Fixed `MemoryBackend` class-level variable shared across instances

---

## Versioning Policy

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

- **MAJOR** version bumps for backward-incompatible API changes
- **MINOR** version bumps for backward-compatible new functionality
- **PATCH** version bumps for backward-compatible bug fixes
