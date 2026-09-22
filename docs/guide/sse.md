# Server-Sent Events (SSE)

This is the third pillar of inguitive. The [Components](components.md) pillar
covers building UI; the [State System](state.md) pillar covers reactive data.
SSE is the server-initiated push layer: the server sends component updates to
the browser at any time, with no user interaction required.

By default, inguitive follows a request-response model: a user action triggers
an HTMX POST, which returns OOB HTML that updates the relevant components.
**SSE support** breaks this constraint.

This unlocks use cases such as:

- Live dashboards (metrics, charts, counters)
- Notifications and alerts
- Presence indicators ("3 users online")
- Progress bars for background jobs

## How it works

Every inguitive page automatically opens a persistent SSE connection to
`GET /_sse`. The same OOB-swap mechanism used by trigger handlers is reused:
the server streams fragments like
`<div id="my-comp" hx-swap-oob="true">…</div>`, and HTMX swaps them into
the page in place.

The SSE connection is wired up by the HTML shell that `ui.page()` renders —
no configuration required.

## Two scopes: global vs. session

inguitive's state system has two scopes, and SSE push follows the scope of the
`State` you mutate:

- **`State`** (global) — `State.set()` from *any* context broadcasts OOB HTML
  to **every** connected session whose components `listen_to` that state. Use
  this for server metrics, system time, global counters.
- **`SessionState`** (per-session) — `SessionState.set()` pushes OOB HTML
  **only** to the session whose context the `.set()` call runs in. Use this
  for per-user notifications, per-user counters, per-user progress.

No explicit push call is needed in either case. Writing the value with
`.set()` is enough — the framework renders the listening components as OOB
swaps and fans them out to the right SSE queues automatically.

## Broadcasting a global value

Call `State.set(value)` from a background task running outside of any request
context. inguitive detects that no session is bound, stores the value as a
global broadcast, and auto-pushes OOB HTML to every connected browser tab
whose components `listen_to` that state.

```python
import asyncio
import datetime

from fastapi import FastAPI

from inguitive import UI, State, Div, Text

app = FastAPI()
ui = UI(app)

clock_state = State("--:--:--", "clock_state")


@app.get("/")
def home():
    return ui.page(
        Div(
            Text(
                lambda: clock_state.get(),
                id="clock-display",
                listen_to=clock_state,      # a State object, not a string
            ),
            css="flex items-center justify-center min-h-screen text-6xl font-mono",
        ),
    )


# Register a startup task that ticks every second. No session is bound here,
# so State.set() broadcasts to all connected clients.
@app.on_event("startup")
async def start_clock():
    asyncio.create_task(_tick())


async def _tick():
    while True:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        clock_state.set(now)      # ← auto-push to every connected client
        await asyncio.sleep(1)
```

See `examples/sse_global_app.py` for a runnable version.

## Pushing to a single session

Use `SessionState` instead of `State`. `SessionState.set()` writes to the
*current* session's isolated data and auto-pushes only to that session's open
SSE connections. The session is "current" in two situations:

1. **Inside a trigger handler.** The middleware has bound the requesting
   session, and `asyncio.create_task(...)` copies that binding into the new
   task.
2. **Inside a `session_context(session_id)` block.** This binds a session by ID
   outside of a request (e.g. a task started from `@app.on_event("startup")`
   that targets a specific user).

The common pattern is (1): start a per-session loop from a trigger handler.

```python
import asyncio

from fastapi import FastAPI

from inguitive import UI, SessionState, Div, Text, Button, session_active

app = FastAPI()
ui = UI(app)

counter_state = SessionState(0, "counter_state")


@ui.trigger_handler
def start_counter():
    # asyncio.create_task copies the current context (including the bound
    # session) into the new task, so SessionState.set() inside _tick targets
    # this user's session without any explicit binding.
    asyncio.create_task(_tick())


async def _tick():
    # session_active() returns True while this session has at least one open
    # SSE connection, and False once they all close — so the loop terminates
    # cleanly when the user closes every tab.
    while session_active():
        await asyncio.sleep(1)
        counter_state.set(counter_state.get() + 1)   # ← auto-push to this session


@app.get("/")
def home():
    return ui.page(
        Div(
            Text(
                lambda: str(counter_state.get()),
                id="counter-display",
                listen_to=counter_state,
            ),
            Button("Start", trigger=start_counter),
        ),
    )
```

See `examples/sse_session_app.py` for a runnable version with an
idempotency guard against double-clicks.

## `session_context`: binding a session outside a request

`session_context(session_id)` is the background-task analog of the request
middleware: it loads a session by ID, makes it the active session so
`State`/`SessionState` operate on *that* user's data, and persists the session
on exit if it was mutated. Use it when you need to write to a session that is
not the one bound by the current request — for example, a task started from
`@app.on_event("startup")` that targets a specific user:

```python
import asyncio

from inguitive import session_context, SessionState, session_active

counter_state = SessionState(0, "counter_state")


async def tick_for_user(session_id: str):
    async with session_context(session_id) as session:
        if session is None:
            return                       # session was evicted — stop
        while session_active():
            await asyncio.sleep(1)
            counter_state.set(counter_state.get() + 1)   # auto-push to this session
```

`.set()` called inside the block triggers the auto-push path: the framework
schedules an OOB update to the session's open SSE queues. No explicit push
call is needed.

The trigger-handler + `asyncio.create_task` pattern (above) is preferred when
the task is started from a request — the session binding comes for free from
contextvar copy semantics. Reach for `session_context` when the task is
started *outside* a request (startup events, webhook handlers, etc.) and you
only have a `session_id` to identify the target.

## `session_active()`: terminating per-session loops

`session_active()` returns `True` while the current session has at least one
open SSE connection, and `False` once they all close. Use it as the loop
condition for per-session background tasks so they stop cleanly when the user
closes every tab:

```python
async def _tick():
    while session_active():
        await asyncio.sleep(1)
        counter_state.set(counter_state.get() + 1)
```

This is the explicit, less-magic alternative to framework-injected task
cancellation: the user writes the termination condition in their own loop, and
the framework does not cancel tasks behind the scenes.

## Idempotency for per-session tasks

A trigger handler can be clicked twice before its task starts. To prevent two
loops writing to the same `SessionState`, guard with a per-worker, in-process
dict keyed by `session_id`:

```python
import asyncio

from inguitive import get_session_id

_counter_tasks: dict[str, asyncio.Task] = {}


@ui.trigger_handler
def start_counter():
    session_id = get_session_id()
    existing = _counter_tasks.get(session_id)
    if existing is not None and not existing.done():
        return                       # already running — refuse the duplicate
    counter_state.set(0)
    task = asyncio.create_task(_tick(session_id))
    _counter_tasks[session_id] = task
    task.add_done_callback(lambda t, sid=session_id: _counter_tasks.pop(sid, None))
```

The live `asyncio.Task` is not JSON-serialisable, so it stays in process memory
(never in `data_registry`, which `RedisBackend` round-trips). The guard must
stay synchronous: if it ever becomes `async` and `await`s between the check and
the store, the atomicity is lost and an `asyncio.Lock` keyed by `session_id`
is needed around that section.

## Using SSE with `RedisBackend`

SSE auto-push works with `RedisBackend` out of the box. Here is how it works
under the hood:

- **Listener metadata is persisted.** Component listener sets (which component
  IDs listen to which state) live in the session's `data_registry`, which is
  serialised to Redis (sets are stored as JSON lists and restored to sets on
  load). The auto-push path can therefore always determine which components
  need re-rendering, regardless of backend.
- **Live components are cached per worker.** Component objects hold arbitrary
  callables and cannot be serialised to Redis. Instead, each worker keeps a
  process-local cache of the live `component_registry` for every session it
  renders. Since an SSE connection is always opened by a browser that loaded
  its page through the *same* worker, that worker's cache always contains the
  components needed to render pushes for its locally-connected clients. Cache
  entries are refreshed on every request and expire after one hour of
  inactivity (or when the session is deleted).

No configuration is required — install the `redis` extra, set
`session_backend=RedisBackend(...)` on `UI(...)`, and auto-push keeps working:

```bash
pip install "inguitive[redis]"
```

```python
from inguitive import UI
from inguitive.backends.redis import RedisBackend

ui = UI(app, session_backend=RedisBackend(redis_url="redis://localhost:6379"))
```

## Limitations and notes

| Topic | Detail |
|---|---|
| **Worker restarts** | The per-worker component cache is in process memory. After a worker restart, sessions loaded from Redis have no cached components until the user reloads a page (which repopulates the cache). Until then, SSE pushes for those sessions are silently skipped. |
| **Multi-worker deployments** | Each worker maintains its own in-memory SSE registry. An auto-push on worker A reaches only clients connected to worker A. The recommended fix is **sticky sessions** at the load balancer (no broker needed). See [Multi-worker deployment](session-backends.md#multi-worker-deployment) in the Session Backends guide. |
| **Missed events** | SSE does not persist events. If the client reconnects after a drop, it will not receive events sent during the disconnection. Components re-render with current state on the next user interaction or page reload. |
| **Keep-alive** | inguitive sends a `heartbeat` comment every 30 seconds to prevent proxies and load balancers from closing idle connections. |
| **Multiple tabs** | Each open tab registers its own SSE stream. All tabs sharing a session ID receive every push (auto-push fans out to all of a session's queues). Closing one tab removes only that tab's connection and does not affect the others. |
