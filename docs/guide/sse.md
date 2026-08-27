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

clock_state = State("--:--:--", "clock_state")


@app.page("/")
def home():
    return Div(
        Text(
            lambda: clock_state.get(), 
            id="clock-display", 
            listen_to="clock_state",
        ),
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

> **"State isolation"**
> 
> When `state.set()` is called from a background task, the value becomes the
> **global broadcast value** — the same value is shown to all users. This is
> correct for server metrics, system time, and similar global data.
>
> Per-user state (e.g. a user-specific notification) should use
> [`push_update()`](#explicit-per-session-push) instead.

## Explicit per-session push

For fine-grained control — pushing to a specific user rather than everyone —
use `push_update(session_id, *component_ids)`.

```python
import asyncio
from inguitive import State, Text, Div, Button, create_app, push_update, get_session_id

app = create_app()
notification_state = State("", "notification_state")

# A dict mapping session_id → queue of pending messages (your app logic)
pending: dict[str, list[str]] = {}


@app.page("/")
def home():
    return Div(
        Text(
            lambda: notification_state.get(),
            listen_to="notification_state",
        ),
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
    await push_update(session_id, *notification_state.listeners)
```

`push_update` is a no-op when the session has no active SSE connection
(e.g. the user closed the tab), so it is always safe to call.

## Recipe: session-scoped background task

The per-session-push example above pushes once. Real work — a live progress
bar, an external feed watcher, a bounded timer — runs a *loop* that updates a
per-user `State` over time. This is the canonical recipe for that, and the
template the `examples/sse_session_app.py` example is built on.

Two pieces, both in your module: a **per-worker task registry** (module-level
dict) and a **loop** that does its work outside `session_context` and enters it
briefly to write `State` and push.

```python
import asyncio

from inguitive import State, get_session_id, push_update, session_context

# 1. Per-worker task registry. The live asyncio.Task is not JSON-serialisable,
#    so it stays in process memory (never in data_registry, which RedisBackend
#    round-trips). Keyed by session_id so different users' loops never collide.
#    ONE DICT PER CONCURRENT WORKFLOW: A session running e.g. both a progress loop
#    and a notification loop needs _progress_tasks and _notification_tasks,
#    otherwise the guard would conflate the two and refuse the second.
_progress_tasks: dict[str, asyncio.Task] = {}

progress_state = State({"done": 0, "total": 0, "status": "idle"}, "progress_state")


# 2. Trigger handler — starts the loop, idempotently. Must stay synchronous:
#    the guard is an atomic check-then-act with no `await` between the read
#    and the store. (See "When to deviate" below for the restart-vs-refuse
#    choice and the async-handler caveat.)
@app.trigger_handler
def start_work():
    session_id = get_session_id()
    existing = _progress_tasks.get(session_id)
    if existing is not None and not existing.done():
        return  # already running — refuse the duplicate start
    progress_state.set({"done": 0, "total": 100, "status": "running"})
    task = asyncio.create_task(_work_loop(session_id))
    _progress_tasks[session_id] = task
    task.add_done_callback(lambda t, sid=session_id: _progress_tasks.pop(sid, None))


# 3. The loop. Work goes OUTSIDE session_context; State writes and pushes go
#    INSIDE. Each iteration's State change is saved when the context exits, so
#    a crash after step 1420 has persisted progress to 1420.
async def _work_loop(session_id: str):
    total = 100
    for done in range(1, total + 1):
        await asyncio.sleep(1)               # OUTSIDE — sleeping is not State work
        result = do_expensive_step(done)     # OUTSIDE — pure computation / I/O

        async with session_context(session_id) as session:   # INSIDE begins
            if session is None:                              # session evicted — stop
                return
            progress_state.set({                               # write per-user State
                "done": done, "total": total, "status": "running",
            })
            await push_update(session_id, *progress_state.listeners)  # render + push
        # context exits → saves the session if dirty

    # Final push: mark complete so the UI can swap in a "done" view. "done" is
    # distinct from "idle" (never started / ready to start) — a restart flips
    # "done" back to "running" by starting again.
    async with session_context(session_id) as session:
        if session is None:                  # session gone between last tick and here
            return
        progress_state.set({"done": total, "total": total, "status": "done"})
        await push_update(session_id, *progress_state.listeners)
```

### What goes inside `session_context`, what stays outside

One rule: **inside goes anything that reads or writes session-scoped `State`;
outside goes everything else.**

| Inside the context | Outside the context |
|---|---|
| `state.set(...)`, `state.get()`, `state.listeners` | Computation, API calls, file I/O |
| `await push_update(session_id, *state.listeners)` | `await asyncio.sleep(...)` |
| `if session is None: return` (the eviction check) | Appending to a local list / accumulator |

Why: `session_context` exists to bind the session so `State` operates on *this
user's* data. Computation and I/O don't need the session, and keeping them out
keeps the commit window tight and the save prompt. Two silent mistakes to
avoid: sleeping *inside* the context delays the save until after the sleep, and
reading `.listeners` *outside* the context returns an empty set (no error) so
the push silently does nothing.

### When to deviate from the template

- **Restart vs. refuse.** The guard above *refuses* a second start while
  running. To *restart* instead (the `examples/sse_session_app.py` counter does
  this), cancel the existing task and reset the state before spawning:
  ```python
  if existing is not None and not existing.done():
      existing.cancel()
  progress_state.set({"done": 0, ...})   # reset
  ```
- **No start button (startup task).** A globally-broadcast counter needs no
  per-session registry, no guard, and no `session_context` — call `State.set()`
  from a `@app.on_event("startup")` task and the framework auto-pushes to all
  tabs. See `examples/sse_global_app.py`.
- **Async trigger handler.** If `start_work` (see example above) ever becomes 
  `async` and `await`s between the check and the store, the guard's atomicity 
  is lost — an `asyncio.Lock` keyed by `session_id` is needed around that section. 
  Keep the handler synchronous if you can.

### Multi-worker note

`_progress_tasks` (see example above) is per-process. With multiple workers, worker 
B's guard sees no task for a session whose loop runs on worker A, and would start a
second loop. The correct deployment is **sticky sessions** (the session, its SSE 
connection, and its loop all live on one worker) — see
[Multi-worker deployment](session-backends.md#multi-worker-deployment). If you
cannot use sticky sessions, guard with a Redis `SET NX` lock instead of the
in-process dict (recipe in the same section).

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
| **Multi-worker deployments** | Each worker maintains its own in-memory SSE registry. A push from worker A will not reach a client connected to worker B. The recommended fix is **sticky sessions** at the load balancer (no broker needed); alternatively publish pushes to a message broker (e.g. Redis Pub/Sub) and call `push_update()` on each worker. See [Multi-worker deployment](session-backends.md#multi-worker-deployment) in the Session Backends guide for both recipes. |
| **Missed events** | SSE does not persist events. If the client reconnects after a drop, it will not receive events sent during the disconnection. Components re-render with current state on the next user interaction or page reload. |
| **Keep-alive** | inguitive sends a `heartbeat` comment every 30 seconds to prevent proxies and load balancers from closing idle connections. |
| **Multiple tabs** | Each open tab registers its own SSE stream. All tabs sharing a session ID receive every push (auto-push and `push_update` both fan out to all tabs). Closing one tab removes only that tab's connection and does not affect the others. |
