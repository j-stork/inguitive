# inguitive Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- 15 built-in components: `Component`, `Div`, `Button`, `Label`, `Icon`, `Input`, `Textarea`, `Select`, `Checkbox`, `Radio`, `Form`, `Text`, `Link`, `TemplateComponent`, `DataTable`
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
