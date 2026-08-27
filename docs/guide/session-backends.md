# Session Backends

inguitive uses session-scoped registries to isolate each user's state,
components, and data. The backend controls where sessions are stored.

## Choosing a backend

| Backend | Use when | Persistence | Multi-worker |
|---|---|---|---|
| `MemoryBackend` | Development, single worker | ❌ Lost on restart | ❌ No |
| `RedisBackend` | Production, multiple workers | ✅ Yes | ✅ Session data — see [Multi-worker deployment](#multi-worker-deployment) |

## `MemoryBackend` (default)

Sessions are stored in RAM. No configuration required — it is the default when
no `session_backend` is passed to `create_app`.

```python
from inguitive import create_app

app = create_app()  # MemoryBackend by default
```

**Limitations:**

- State is lost when the process restarts.
- Sessions are not shared across multiple uvicorn workers. Run with a single
  worker in development (`inguitive run` does this by default).

## `RedisBackend`

Sessions are serialised to Redis. Requires the `redis` extra:

```bash
pip install "inguitive[redis]"
```

```python
from inguitive import create_app, RedisBackend

app = create_app(
    session_backend=RedisBackend(
        redis_url="redis://localhost:6379",
        ttl_seconds=3600,    # session timeout in seconds (default: 3600)
    )
)
```

**Advantages:**

- Sessions survive process restarts.
- Session data is shared across any number of uvicorn workers or replicas.
- Cleanup is automatic — Redis expires keys via its built-in TTL mechanism.

> **Multi-worker caveat:** `RedisBackend` shares *session data* across workers, but
> not the live, non-serialisable objects that live in worker memory — SSE
> connection queues, the component registry cache, and any background tasks you
> start. See [Multi-worker deployment](#multi-worker-deployment) for how to make
> SSE pushes and background tasks correct under multiple workers.

## Session lifetime

Sessions are created automatically on the first request and tracked via a
cookie.

| Aspect | MemoryBackend | RedisBackend |
|---|---|---|
| Created | First request | First request |
| Expires after | `ttl_seconds` of inactivity | `ttl_seconds` (hard TTL) |
| Cleanup | Periodic via `cleanup_expired()` | Automatic (Redis TTL) |
| Survives restart | ❌ | ✅ |

## Production configuration

```python
from inguitive import create_app, RedisBackend

app = create_app(
    title="My App",
    session_backend=RedisBackend(redis_url="redis://localhost:6379"),
    session_cookie_secure=True,       # HTTPS only
    session_cookie_httponly=True,     # no JS access (default: True)
    session_cookie_max_age=86400,     # 24-hour browser-side expiry
)
```

**Production checklist:**

- ✅ Use `RedisBackend` for persistence and multi-worker session data
- ✅ Use sticky sessions (or a message broker) for SSE pushes and background tasks — see [Multi-worker deployment](#multi-worker-deployment)
- ✅ Set `session_cookie_secure=True` when serving over HTTPS
- ✅ Set `dev_mode=False` to suppress development warnings
- ✅ Deploy with HTTPS (required for secure cookies)

## Multi-worker deployment

inguitive is a stateful-server framework: each worker keeps live, in-memory
state that cannot be serialised to a backend — SSE connection queues, the
component registry cache, and any background tasks you start with
`asyncio.create_task`. `RedisBackend` shares *session data* across workers, but
it cannot share these live objects.

There are two correct ways to deploy multiple workers. Pick one.

### Option A — Sticky sessions (recommended)

Pin each session cookie to a single worker at the load balancer. A session's
SSE connection, component cache, and background tasks then all live on one
worker for the session's lifetime, so the existing per-worker model is correct
with no broker and no cross-worker fanout. This is the standard pattern for
stateful servers and needs no framework support.

```nginx
# nginx — hash on the session cookie so each user lands on one worker
upstream inguitive {
    ip_hash;            # or: hash $cookie_<cookie_name> consistent;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

```yaml
# Traefik
http:
  services:
    inguitive:
      sticky:
        cookie: true
```

The cookie name is whatever you pass to `create_app(..., session_cookie_name=)`
(default `inguitive_session`). Hash on that.

### Option B — Message broker (broker-optional, opt-in)

If you cannot use sticky sessions, publish each push to a shared broker and
have every worker subscribe and forward to its locally-connected clients.
inguitive leaves the broker choice to you (Redis Pub/Sub, NATS, RabbitMQ, …)
so it does not add a messaging dependency for users who don't need it.

The recipe is ~10 lines. For Redis Pub/Sub, publish a small payload and have
each worker run a subscriber that calls `push_update(session_id, *component_ids)`
for its own locally-connected sessions:

```python
import asyncio
import json
import redis.asyncio as redis

async def start_fanout_subscriber(redis_url: str):
    """Subscribe to push events and forward to locally-connected SSE clients."""
    r = redis.Redis.from_url(redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe("inguitive:push")
    async for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        data = json.loads(msg["data"])
        session_id = data["session_id"]
        component_ids = data["component_ids"]
        # push_update is a no-op for sessions with no local SSE connection,
        # so it is safe to call on every worker.
        await push_update(session_id, *component_ids)


async def publish_push(redis_url: str, session_id: str, *component_ids: str):
    r = redis.Redis.from_url(redis_url)
    await r.publish("inguitive:push", json.dumps({
        "session_id": session_id,
        "component_ids": list(component_ids),
    }))
```

For cross-worker idempotency of background tasks (e.g. the counter loop in
`src/inguitive/examples/sse_session_app.py`), use a Redis lock instead of the per-worker dict:

```python
async def acquire_task_lock(redis_url: str, session_id: str, ttl: int = 30) -> bool:
    """Atomically claim a per-session task. Returns True if this worker won it."""
    r = redis.Redis.from_url(redis_url)
    # SET key 1 NX EX ttl — succeeds only if the key does not exist.
    return bool(await r.set(f"task_lock:{session_id}", "1", nx=True, ex=ttl))


async def release_task_lock(redis_url: str, session_id: str) -> None:
    r = redis.Redis.from_url(redis_url)
    await r.delete(f"task_lock:{session_id}")
```

A worker that loses the lock does not start the task; the winner refreshes the
TTL while running and releases the lock when it stops.

!!! note
    The examples above are recipes, not built-in framework APIs. inguitive ships
    no broker integration so you can choose the one that fits your stack — and
    so single-worker deployments carry no messaging overhead.
