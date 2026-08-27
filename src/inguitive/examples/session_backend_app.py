"""
Session backends example using inguitive.

Run with: uvicorn inguitive.examples.session_backend_app:app --reload
      (MemoryBackend, default)
      SESSION_BACKEND=redis REDIS_URL=redis://localhost:6379 \\
          uvicorn inguitive.examples.session_backend_app:app --reload
      (RedisBackend)

Switching Session Backends
--------------------------
This example demonstrates how to swap inguitive's session storage backend
via ``set_session_backend()``. The backend controls where per-session state
lives; the rest of the app code is identical regardless of backend.

Two backends ship with the framework:

| Backend          | Use when                         | Persistence      | Multi-worker |
|------------------|----------------------------------|------------------|--------------|
| ``MemoryBackend`` | Development, single worker      | Lost on restart  | No           |
| ``RedisBackend``  | Production, multiple workers    | Survives restart | Yes (data)   |

The backend is chosen at startup from the ``SESSION_BACKEND`` env var and
registered with ``set_session_backend()`` before the app handles requests.
``MemoryBackend`` is the default and needs no extra deps; ``RedisBackend``
requires the ``redis`` package and a running Redis server (configure its URL
via ``REDIS_URL``). See ``docs/guide/session-backends.md`` for the full
deployment notes, including sticky sessions and brokers for multi-worker SSE.

The page reports which backend is active (read once at startup, since
``get_session_backend()`` returns the live object) and shows a per-session
counter so you can confirm isolation still holds under either backend — the
same mechanism as ``counter_app.py``, just on a different storage layer.

To test:
1. Run with the default (MemoryBackend) — increment the counter in two
   windows; each session is independent, and state is lost on restart
2. Run with ``SESSION_BACKEND=redis`` (and a Redis server up) — increment in
   two windows; state survives a server restart
3. In both cases the page shows which backend is serving the session
"""

import os

from inguitive import (
    Button,
    Div,
    MemoryBackend,
    RedisBackend,
    State,
    Text,
    create_app,
    get_session_backend,
    get_session_id,
    set_session_backend,
    update_components,
)

from .css import BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS

# --- Backend Selection ---
# Choose the session backend at startup from the SESSION_BACKEND env var.
# This must happen before create_app() wires middleware, so the module-level
# code below runs at import time.
_backend_name = os.getenv("SESSION_BACKEND", "memory").lower()
if _backend_name == "redis":
    # RedisBackend lazily connects on first use; missing `redis` package or
    # an unreachable server only surfaces when a request touches the backend.
    set_session_backend(
        RedisBackend(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))
    )
else:
    set_session_backend(MemoryBackend())


# --- App Setup ---
app = create_app()


# --- State Instances ---
counter_state = State(0, "counter_state")


# --- Trigger Handlers ---
@app.trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)


@app.trigger_handler
def reset():
    counter_state.set(0)
    return update_components(*counter_state.listeners)


# --- Components ---
def backend_name() -> str:
    """Human-readable name of the active backend class."""
    return type(get_session_backend()).__name__


def Counter() -> Div:  # noqa: N802
    return Div(
        Text(
            lambda: f"Count: {counter_state.get()}",
            id="counter-label",
            css="text-xl text-center text-slate-900",
            listen_to="counter_state",
        ),
        Button("+1", trigger="increment", css=f"{BUTTON_PRIMARY_CSS} w-full"),
        Button("Reset", trigger="reset", css=f"{BUTTON_SECONDARY_CSS} w-full"),
        Text(
            lambda: f"Session: {get_session_id()}",
            css="text-sm text-center text-slate-600",
        ),
        Text(
            f"Backend: {backend_name()}",
            css="text-sm text-center text-slate-500",
        ),
        id="counter-card",
        css="rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm",
    )


# --- Routes ---
@app.page("/")
def home():
    return Div(
        Counter(),
        css="min-h-screen flex items-center justify-center bg-slate-100",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.session_backend_app:app", host="0.0.0.0", port=8000, reload=True)
