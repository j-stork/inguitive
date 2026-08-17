# Server-Sent Events (SSE)

By default, inguitive follows a request-response model: a user action triggers
an HTMX POST, which returns OOB HTML that updates the relevant components.
**SSE support** breaks this constraint — the server can push component updates
to the browser at any time, with no user interaction required.

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

The HTMX SSE extension is loaded automatically from the bundled `base.html`
template — no configuration required.

## Broadcasting from a background task

The simplest pattern: call `state.set(value)` from an `asyncio` task running
outside of a request context. inguitive detects that there is no active
session, stores the value as a global broadcast, and automatically pushes OOB
HTML to every connected browser tab whose components listen to that state.

```python
import asyncio
from inguitive import State, Text, Div, create_app

app = create_app()

clock_state = State("--:--", "clock")


@app.page("/")
def home():
    return Div(
        Text(lambda: clock_state.get(), id="clock-display", listen_to="clock"),
        css="flex items-center justify-center min-h-screen text-6xl font-mono",
    )


# Register a startup task that ticks every second
@app.on_event("startup")
async def start_clock():
    asyncio.create_task(_tick())


async def _tick():
    import datetime

    while True:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        clock_state.set(now)      # ← triggers SSE push to all connected clients
        await asyncio.sleep(1)
```

!!! note "State isolation"
    When `state.set()` is called from a background task, the value becomes the
    **global broadcast value** — the same value is shown to all users. This is
    correct for server metrics, system time, and similar global data.

    Per-user state (e.g. a user-specific notification) should use
    [`push_update()`](#explicit-per-session-push) instead.

## Explicit per-session push

For fine-grained control — pushing to a specific user rather than everyone —
use `push_update(session_id, *component_ids)`.

```python
import asyncio
from inguitive import State, Text, Div, Button, create_app, push_update, get_session_id

app = create_app()
notification_state = State("", "notification")

# A dict mapping session_id → queue of pending messages (your app logic)
pending: dict[str, list[str]] = {}


@app.page("/")
def home():
    return Div(
        Text(lambda: notification_state.get(), id="notification", listen_to="notification"),
        Button("Request update", trigger="request_update"),
        css="flex flex-col gap-4 p-8",
    )


@app.trigger_handler
def request_update():
    session_id = get_session_id()
    # Schedule a push to only this session
    asyncio.create_task(_delayed_push(session_id))


async def _delayed_push(session_id: str):
    await asyncio.sleep(2)          # simulate background work
    await push_update(session_id, "notification")
```

`push_update` is a no-op when the session has no active SSE connection
(e.g. the user closed the tab), so it is always safe to call.

## API reference

::: inguitive.fastapi.push_update
    options:
      show_source: false

## Using SSE with RedisBackend

SSE auto-push and `push_update()` both work with `RedisBackend` out of the box.
Here is how it works under the hood:

- **Listener metadata is persisted.** Component listener sets (which component
  IDs listen to which state) live in the session's `data_registry`, which is
  serialised to Redis (sets are stored as JSON lists and restored to sets on
  load). `_push_sse_for_state` can therefore always determine which components
  need re-rendering, regardless of backend.
- **Live components are cached per worker.** Component objects hold arbitrary
  callables and cannot be serialised to Redis. Instead, each worker keeps a
  process-local cache of the live `component_registry` for every session it
  renders. Since an SSE connection is always opened by a browser that loaded
  its page through the *same* worker, that worker's cache always contains the
  components needed to render pushes for its locally-connected clients. Cache
  entries are refreshed on every request and expire after one hour of
  inactivity (or when the session is deleted).

No configuration is required — switch `session_backend=RedisBackend(...)` and
both broadcast auto-push and per-session `push_update()` keep working.

## Limitations and notes

| Topic | Detail |
|---|---|
| **Worker restarts** | The per-worker component cache is in process memory. After a worker restart, sessions loaded from Redis have no cached components until the user reloads a page (which repopulates the cache). Until then, SSE pushes for those sessions are silently skipped. |
| **Multi-worker deployments** | Each worker maintains its own in-memory SSE registry. A push from worker A will not reach a client connected to worker B. Use a message broker (e.g. Redis Pub/Sub) and call `push_update()` on each worker so all workers forward messages to their locally-connected clients. |
| **Missed events** | SSE does not persist events. If the client reconnects after a drop, it will not receive events sent during the disconnection. Components re-render with current state on the next user interaction or page reload. |
| **Keep-alive** | inguitive sends a `heartbeat` comment every 30 seconds to prevent proxies and load balancers from closing idle connections. |
| **Multiple tabs** | Each open tab registers its own SSE stream. All tabs sharing a session ID receive every push (auto-push and `push_update` both fan out to all tabs). Closing one tab removes only that tab's connection and does not affect the others. |
