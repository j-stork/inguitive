# Inguitive TODO

Tasks are ordered descending by urgency.

---

## (Done) 1 — Critical: HTML escaping in component rendering (XSS)

`components.py` builds HTML via string concatenation without escaping user-supplied values. Any component that receives data derived from user input (form fields, URL parameters, chat messages, etc.) and renders it directly will inject raw HTML into the page. `html.escape()` must be applied at the `_resolve` boundary for all text content and attribute values before any user-facing deployment.

---

## (Done) 2 — High: Silent failure when `listen_to` is not declared

When a `State` object is mutated but no component declares `listen_to` for that state, nothing re-renders and no error or warning is raised. This is the most common footgun in the current design: the bug is invisible and the UI simply goes stale. A dev-mode warning — e.g. "State `x` was mutated but no component is listening" — would catch this class of mistake immediately.

### (Done) Issue 1 — `create_app(dev_mode=False)` cannot disable warnings that are already on

`enable_dev_mode_warnings()` is a one-way setter. There is no corresponding `disable_dev_mode_warnings()`. The `dev_mode=False` branch in `create_app()` simply does nothing:

```
if dev_mode: 
    # dev_mode=False → this branch is skipped entirely
    from inguitive.state import enable_dev_mode_warnings 
    enable_dev_mode_warnings()
```

If any previous call in the same process set the flag to `True` — another `create_app()`, a test, an import side-effect — passing `dev_mode=False` to a subsequent `create_app()` silently fails to achieve its stated purpose. The flag can only ever go `False → True` via the public API, never back. In production this matters: a production process that also runs any test harness that calls `create_app()` with defaults would have warnings permanently active with no way to turn them off through the documented interface.

The test suite confirms this is a real gap: the `reset_dev_mode` fixture is forced to directly manipulate the private `_dev_mode_warnings_enabled` attribute because there is no public function to reset it:

` state_module._dev_mode_warnings_enabled = False # forced to reach into internals `

A `disable_dev_mode_warnings()` function is missing from `state.py`.

---

### (Done) Issue 2 — Python's warning deduplication will suppress the warning after the first occurrence

`warnings.warn()` is subject to Python's built-in deduplication filter. By default, a `UserWarning` from a given `(message, category, module, lineno)` tuple is only shown once per location for the lifetime of the process. In a running web server handling repeated requests, the warning fires on the first trigger invocation and is silently swallowed on every subsequent one. A developer who does not have their terminal open at exactly the right moment will never see it again, which defeats the entire purpose of a development diagnostic.

This is a meaningful practical failure mode. `logging.warning()` does not have this suppression behaviour and is more appropriate for a runtime framework diagnostic. Alternatively, `warnings.warn()` could be paired with `warnings.simplefilter("always", UserWarning)` in `enable_dev_mode_warnings()`, but that is a blunt instrument that affects all `UserWarning`s in the process. Using `logging` is the cleaner fix.

---

### (Done, no changes) Issue 3 — The warning is checked against the session listener set, but `State.set()` can be called before the session's component has rendered

The `listeners` property reads from `_get_data_registry()` — the current session's data store. A component only adds itself as a listener when it is rendered. On the very first request for a brand-new session, the sequence is:

1. Page handler runs → components render → `add_listener()` registers the component
2. User interacts → trigger handler fires → `State.set()` is called

Step 2 happens after step 1, so the listener is present in the session by the time `set()` is called. That is the happy path and it works. ✓

However: if a developer calls `State.set()` in a FastAPI `startup` event handler or any context that runs before a session exists, `self.listeners` will call `_get_data_registry()` on a session that hasn't been initialised. `State.set()` already calls `_get_data_registry()` on line 93 before the warning check, so if there is no active session, it will fail there first — the warning code does not introduce a new failure mode. This is a pre-existing constraint but it is worth noting that the warning is only meaningful within an active request context.

---

### Summary

| #   | Severity | Issue |
| --- | --- | --- |
| 1   | Bug | No `disable_dev_mode_warnings()` — `create_app(dev_mode=False)` cannot undo a previously enabled flag; tests must reach into private state |
| 2   | Bug | Python's warning deduplication suppresses the warning after the first occurrence per call site, making it unreliable in a live server |
| 3   | Note | Warning is only meaningful within an active request context; no new failure mode, but worth documenting |

Task #2 is not correctly implemented as-is. Issues 1 and 2 both need to be addressed before the implementation is reliable.

---

## (Done) 3 — High: `MemoryBackend` is not thread-safe

`MemoryBackend` stores sessions in a plain `dict` with no locking. Under concurrent async requests or a multi-threaded server, this is a data race. Should be documented explicitly as development-only, and an `asyncio.Lock` should be added to guard reads and writes.

### Steps

Step 1: Update the Abstract Base Class
- In session.py: Change SessionBackend abstract methods to be async
- get_session, save_session, delete_session, cleanup_expired → all async def

Step 2: Update MemoryBackend
- In session.py: Import asyncio
- Add self._lock = asyncio.Lock() in __init__
- Make all four methods async and wrap their bodies in async with self._lock:

Step 3: Update RedisBackend
- In session.py: Make all four methods async
- Wrap bodies in async with self._lock: (add lock to __init__)
- Note: Redis client calls may already be synchronous or async — verify behavior

Step 4: Update fastapi.py Middleware
- In fastapi.py: Add await before every backend method call:
- backend.cleanup_expired() → await backend.cleanup_expired()
- backend.get_session(...) → await backend.get_session(...)
- backend.save_session(...) → await backend.save_session(...)
- The middleware's __call__ is already async, so this is just adding keywords

Step 5: Update session.py Helper Functions
- In session.py: Functions that call backend methods need await:
- _get_current_session() calls backend.get_session()
- _get_or_create_current_session() calls backend.save_session()
- These helpers may need to become async themselves

Step 6: Update Tests
- In test_session_backends.py: Add await before all backend method calls
- All test methods that call backend methods need to become async
- Same for test_state_isolation.py, test_state_warnings.py, test_xss_escaping.py, test_components.py

Step 7: Check the entire implementation

### (Done) Improvements

**`MemoryBackend` is correctly implemented.** `asyncio.Lock()` is in `__init__`, all four methods are `async def`, and every body is wrapped in `async with self._lock`. ✓

**`RedisBackend` is not correctly fixed.** It follows the same structural pattern — `async def` methods, `asyncio.Lock()`, `async with self._lock` — but the Redis client calls inside are all **synchronous**, using the standard `redis.Redis` client rather than `redis.asyncio`:

```python
async def get_session(self, session_id):
    async with self._lock:
        client = self._get_client()   # synchronous redis.Redis
        data = client.get(key)        # blocks the event loop
```

`async with self._lock` only prevents concurrent asyncio tasks from entering the block simultaneously. It does not make blocking I/O non-blocking. A `client.get()` call still holds the event loop hostage for the duration of the network round-trip. The `asyncio.Lock` in `RedisBackend` is therefore ineffective: no two tasks can be suspended inside the lock anyway, because the synchronous Redis call prevents any other coroutine from running while it executes.

The correct fix requires switching the Redis client to `redis.asyncio` (the async interface shipped with `redis>=4.2`):

```python
import redis.asyncio as aioredis

self._client = aioredis.Redis.from_url(self._redis_url, db=self._db, decode_responses=True)
data = await client.get(key)
client.aclose()  # async close
```

Additionally, `cleanup_expired` in `RedisBackend` acquires the lock before returning `0` — the lock is entirely unnecessary there since the method body does nothing (Redis handles TTL automatically).

---

## (Done) 4 — Medium: Unconditional session save on every request

`fastapi.py` middleware saves the full session object in the `finally` block of every request, regardless of whether anything changed. For `RedisBackend` with non-trivial session data this is unnecessarily expensive. A dirty-flag pattern (mark session as modified on `State.set` or explicit write, save only if dirty) would avoid redundant serialisation and network round-trips.

---

## (Done) 5 — Medium: No possibility to inject individual content to `<head>`

Currently there's no (easy) way to add content to the `<head>` of a page like `<meta>` or `<link>` tags. 

### (Done) Improvements

1. **(Done)** Type hint precision - Any in _PageDecorator and function signatures could be str | Component | list[str | Component] | None for clarity.
2. **(Done)** markupsafe.Markup support _render_template_content() should detect markupsafe.Markup and return it unchanged (like _resolve() in components.py does) to prevent double-escaping edge cases.
3. **(Done)** Documentation: The `title` and `favicon` parameters of `create_app()` and `@app.page()` are already demonstrated in README.md. The newly added `head` parameter does not appear, yet. A short note in the README about the feature would help users discover it.

---

## (Done) 6 — Medium: `Icon._replace_class` uses fragile string manipulation

SVG class attribute replacement is implemented with `str.find` and string slicing rather than an XML parser. Slightly non-standard SVGs (self-closing tags, extra whitespace, multiple class attributes) will silently produce broken or incorrect output. Should be replaced with an `xml.etree` or `re`-based approach.

### Improvements (Done)

The move to `xml.etree.ElementTree` is a clear improvement over the previous string slicing, and raising `ValueError` with a descriptive message on `ET.ParseError` is the right behaviour.

**`method="html"` → `method="xml"`** (fixed in commit `4156cb09`): `ET.tostring` now uses XML serialisation rules, correct for SVG.

**Namespace prefix preservation** (fixed): The previous regex `re.sub(r'(\s)\w+:', r'\1', result)` stripped any namespace prefix directly. The commit narrowed this to `ns\d+:`, but this was insufficient: ElementTree *always* renames all namespace prefixes to its own `ns0:`, `ns1:`, … scheme during serialisation, regardless of the original names. This meant `xlink:href` was renamed to `ns0:href` by ET before the regex even ran, and then the `ns\d+:` regex still stripped it — same broken outcome via a different path. The test added by that commit passed vacuously because `'href="#target"' in result` is a substring of both `xlink:href="#target"` and `href="#target"`.

Fix: add `ET.register_namespace()` calls at module level in `components.py` for the SVG, xlink, and xml namespaces. ET respects registered prefixes during serialisation and uses them directly instead of generating `ns0:`/`ns1:` placeholders. With this in place, `xlink:href` serialises as `xlink:href`, the `ns\d+:` regexes have nothing to touch, and the prefix is preserved. The test assertion was also tightened to `assert 'xlink:href="#target"' in result`.

---

## (Done) 7 — Medium: No dev-mode error page

Unhandled exceptions in page or trigger handlers surface as raw FastAPI 500 responses. A styled in-browser error page showing the traceback (gated on a dev/debug flag) would make debugging significantly faster and is expected behaviour in a developer-facing framework.

### Improvements

The exception handler, `app.state.dev_mode` forwarding, and the template structure are all correct. One bug:

**`{{ traceback }}` in `error.html` is not HTML-escaped.** The Jinja2 `Environment` is created without `autoescape=True`:

```python
env = Environment(loader=loader)   # autoescape defaults to False
```

Python tracebacks routinely contain `<` and `>` characters — for example `File "<frozen importlib._bootstrap>", line 241` or `<module>` as a frame name. Without escaping, these are interpreted as HTML tags by the browser. The `<frozen importlib._bootstrap>` fragment is treated as an unknown element and its text content is hidden, meaning the traceback panel shows corrupted or truncated output for almost any real exception.

The fix is to escape the variable in the template:

```html
<pre class="...">{{ traceback | e }}</pre>
```

The same applies to `request_method` and `request_url` in `error.html`, though those are framework-generated values and not attacker-controlled, so the practical risk is low.

---

## 8 — Low: `inguitive init --example` flag

`inguitive init` only scaffolds a minimal blank starter. An `--example` flag that lets the user choose one of the bundled example apps (counter, todo, chat) as their starting point would lower the barrier to entry further and demonstrate framework features from the first run.

---

## 9 — Low: Form validation layer

Trigger handlers currently receive raw `multipart` form data as untyped strings with no validation or coercion. A lightweight declarative validation layer (type coercion, required fields, error messages) would reduce boilerplate in every form-based handler and prevent a whole class of runtime errors.

---

## 10 — Low: Auto-wiring state listeners

The `listen_to` parameter requires developers to manually declare which state name each component depends on. An opt-in mechanism — e.g. a `@state.component` decorator or context-manager-based tracking — that registers the dependency automatically during the first render would eliminate the silent failure described in task 2 entirely.

---

## 11 — Expansion: WebSocket / SSE support for server-initiated updates

The current model is strictly request-response (user action → HTMX POST → OOB swap). There is no mechanism for the server to push updates without a user event. Adding Server-Sent Events (SSE) or WebSocket support would unlock real-time use cases: live dashboards, notifications, collaborative editing, and presence indicators.

---

## 12 — Expansion: Higher-level component library

The built-in components cover primitive HTML elements. A set of composites covering common UI patterns — Modal, Toast/notification, Dropdown, Tabs, Pagination, Accordion — would dramatically reduce the code a user has to write and make inguitive competitive with higher-level frameworks out of the box.

---

## 13 — Expansion: Opinionated deployment guide

The README has a production checklist but no concrete deployment walkthrough. A guide covering at least one container-based path (Docker + `gunicorn`/`uvicorn` workers) and one platform-as-a-service option would help developers who have not previously deployed a Python async web app reach production without leaving the inguitive documentation.
