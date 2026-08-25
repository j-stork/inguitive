# inguitive Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
