# Session Backends

inguitive uses session-scoped registries to isolate each user's state,
components, and data. The backend controls where sessions are stored.

## Choosing a backend

| Backend | Use when | Persistence | Multi-worker |
|---|---|---|---|
| `MemoryBackend` | Development, single worker | ❌ Lost on restart | ❌ No |
| `RedisBackend` | Production, multiple workers | ✅ Yes | ✅ Yes |

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
- Works with any number of uvicorn workers or replicas.
- Cleanup is automatic — Redis expires keys via its built-in TTL mechanism.

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

- ✅ Use `RedisBackend` for persistence and multi-worker support
- ✅ Set `session_cookie_secure=True` when serving over HTTPS
- ✅ Set `dev_mode=False` to suppress development warnings
- ✅ Deploy with HTTPS (required for secure cookies)
