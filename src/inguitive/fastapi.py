"""
FastAPI integration for inguitive.
"""

from __future__ import annotations

import asyncio
import importlib.resources
import inspect
import uuid
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import markupsafe
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from inguitive.components import Component
from inguitive.htmx import update_components
from inguitive.session import (
    _SESSION_MIDDLEWARE_MISSING_MSG,
    Session,
    SessionBackend,
    _cache_component_registry,
    _clear_current_session,
    _hydrate_component_registry,
    _register_sse_connection,
    _require_current_session,
    _set_current_session,
    _unregister_sse_connection,
    get_session_backend,
    set_session_backend,
)
from inguitive.state import (
    _get_mutated_states,
    _track_mutations,
)
from inguitive.trigger import _trigger_args_context

# Type alias for head content (supports strings, Components, Markup, lists, or None)
HeadContent = str | Component | markupsafe.Markup | list[str | Component | markupsafe.Markup] | None


def _render_template_content(value: HeadContent) -> str:
    """Render a value (Component, list, string, or Markup) to HTML string for template injection.

    Args:
        value: A string, Component instance, markupsafe.Markup, list of strings/Components/Markup, or None

    Returns:
        Rendered HTML string (safe for template insertion)
    """
    if value is None:
        return ""
    if isinstance(value, markupsafe.Markup):
        # Already marked as safe, don't escape - return as string
        return str(value)
    if isinstance(value, list):
        return "".join(_render_template_content(item) for item in value)
    if hasattr(value, "render") and callable(value.render):
        return value.render()
    return str(value)



def _render_page_shell(content: str, title: str, favicon: str, head_extra: str) -> str:
    """Render a full HTML document shell wrapping the given content.

    Replaces the former base.html Jinja2 template with inline Python string
    composition. The shell includes HTMX + SSE extension, Tailwind CSS, Inter
    font, the hidden #hx-target div for SSE auto-connect, and the pagehide
    cleanup script.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link rel="icon" href="{favicon}">
        <!-- HTMX -->
        <script src="https://unpkg.com/htmx.org@1.9.6"></script>
        <!-- HTMX SSE extension — enables server-initiated component updates -->
        <script src="https://unpkg.com/htmx.org@1.9.6/dist/ext/sse.js"></script>
        <!-- Tailwind CSS -->
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <!-- Inter Font -->
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        <!-- Configure Tailwind to use Inter as default sans-serif -->
        <style type="text/tailwindcss">
            @theme {{
                --font-sans: Inter, sans-serif;
            }}
        </style>
        {head_extra}  <!-- Custom head content injection -->
    </head>
    <body class="min-h-screen">
        {content}
        <!-- Hidden target for HTMX requests (POST triggers and SSE updates) -->
        <div id="hx-target"
             hx-ext="sse"
             sse-connect="/_sse"
             sse-swap="message"
             style="display: none;"></div>
        <!-- Close the SSE EventSource when the page is unloaded so the
             server detects the disconnect immediately and frees the
             connection slot.  Without this, the browser holds the
             connection open until the server's 0.5s disconnect poll fires,
             which exhausts the browser's per-origin connection limit
             (6 for HTTP/1.1) during rapid page navigation and blocks
             subsequent page loads.

             We trigger the SSE extension's own cleanup event
             (htmx:beforeCleanupElement) rather than calling
             htmx.getInternalData directly, because getInternalData is an
             internal API not exposed on the public htmx object. -->
        <script>
            window.addEventListener("pagehide", function () {{
                var elt = document.getElementById("hx-target");
                if (elt && typeof htmx !== "undefined") {{
                    htmx.trigger(elt, "htmx:beforeCleanupElement");
                }}
            }});
        </script>
    </body>
</html>"""


def _register_trigger_route(app, trigger_name: str, handler: Callable):
    """Helper to register a trigger route on an app."""

    @app.post(f"/_trigger/{trigger_name.lstrip('/')}", response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler, tn=trigger_name):
        _require_current_session()
        sig = inspect.signature(h)
        needs_request = "request" in sig.parameters
        is_async = inspect.iscoroutinefunction(h)

        kwargs: dict[str, Any] = {}
        if needs_request:
            kwargs["request"] = request

        # Extract query params which contain trigger_args from Component
        query_params = dict(request.query_params)

        # Track state mutations during handler execution for auto-propagation
        with _track_mutations():
            # Set trigger_args in context for get_trigger_args() access
            with _trigger_args_context(query_params):
                result = await h(**kwargs) if is_async else h(**kwargs)

                # If handler returned explicit response, use it (allows overriding auto-propagation)
                if result:
                    return result

                # Otherwise, auto-generate OOB response from mutated states
                mutated_states = _get_mutated_states()
                all_component_ids: set[str] = set()
                for state in mutated_states:
                    all_component_ids.update(state.listeners)

                return update_components(*all_component_ids)


def trigger_handler_decorator(app, trigger_name: str | None | Callable = None):
    """Register a trigger handler callable, exposed as ``ui.trigger_handler``.

    Called by ``UI.trigger_handler`` with the bound ``app``. Supports two
    call styles:

    - ``@ui.trigger_handler`` (no parentheses): the handler is registered
      under its own function name.
    - ``@ui.trigger_handler("name")`` (with parentheses): the handler is
      registered under the explicit name ``"name"``.

    The handler is stored in ``app.state.trigger_handlers`` and registered
    as a POST route at ``/_trigger/<name>`` via
    :func:`_register_trigger_route`. Trigger arguments sent from
    components are available inside the handler via
    :func:`inguitive.get_trigger_args`.

    Args:
        app: The FastAPI application to register the handler on. Bound
            automatically when attached as ``app.trigger_handler``.
        trigger_name: Either a callable (used directly when the decorator
            is applied without parentheses) or a string name, or None to
            fall back to the function's ``__name__``.

    Returns:
        When applied without parentheses, returns the handler unchanged.
        When applied with parentheses, returns a decorator that does the
        same.

    Usage:
        @app.trigger_handler
        def increment():
            counter_state.set(counter_state.get() + 1)
    """
    if callable(trigger_name):
        # Called as @app.trigger_handler (without parentheses)
        # trigger_name is actually the function
        func = trigger_name
        actual_trigger_name = func.__name__
        app.state.trigger_handlers[actual_trigger_name] = func
        _register_trigger_route(app, actual_trigger_name, func)
        func._inguitive_trigger_url = f"/_trigger/{actual_trigger_name}"  # type: ignore[attr-defined]
        return func
    else:
        # Called as @app.trigger_handler("name") (with parentheses)
        # trigger_name is the name string
        def decorator(func: Callable):
            actual_trigger_name = trigger_name or func.__name__
            app.state.trigger_handlers[actual_trigger_name] = func
            _register_trigger_route(app, actual_trigger_name, func)
            func._inguitive_trigger_url = f"/_trigger/{actual_trigger_name}"  # type: ignore[attr-defined]
            return func

        return decorator


class SessionMiddleware:
    """FastAPI/Starlette ASGI middleware for session management."""

    def __init__(
        self,
        app,
        session_cookie_name: str = "inguitive_session_id",
        session_cookie_max_age: int = 3600,
        session_cookie_secure: bool = False,
        session_cookie_httponly: bool = True,
        cleanup_interval: int = 100,
    ):
        """Initialize SessionMiddleware.

        Args:
            app: The ASGI application
            session_cookie_name: Name of the session cookie
            session_cookie_max_age: Cookie max age in seconds
            session_cookie_secure: Whether cookie is secure (HTTPS only)
            session_cookie_httponly: Whether cookie is HTTP-only
            cleanup_interval: Call cleanup_expired() every N requests (default: 100)
        """
        self.app = app
        self.session_cookie_name = session_cookie_name
        self.session_cookie_max_age = session_cookie_max_age
        self.session_cookie_secure = session_cookie_secure
        self.session_cookie_httponly = session_cookie_httponly
        self.cleanup_interval = cleanup_interval
        self._request_count = 0

    async def __call__(self, scope, receive, send):
        """Process ASGI request with session management."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Periodic cleanup of expired sessions
        self._request_count += 1
        if self._request_count % self.cleanup_interval == 0:
            backend = get_session_backend()
            await backend.cleanup_expired()

        # Extract cookies from headers
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode("latin-1")
        cookies = {}
        for part in cookie_header.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()

        session_id = cookies.get(self.session_cookie_name)
        backend = get_session_backend()

        if session_id:
            session = await backend.get_session(session_id)
            if session is None:
                session = Session(session_id=session_id)
                # Mark as dirty so the finally block below will save this new session
                session.mark_dirty()
        else:
            session = Session(session_id=str(uuid.uuid4()))
            # Mark as dirty so the finally block below will save this new session
            session.mark_dirty()

        _set_current_session(session)

        async def send_with_cookie(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                cookie_value = (
                    f"{self.session_cookie_name}={session.session_id}; "
                    f"Max-Age={self.session_cookie_max_age}; Path=/; SameSite=Lax"
                )
                if self.session_cookie_httponly:
                    cookie_value += "; HttpOnly"
                if self.session_cookie_secure:
                    cookie_value += "; Secure"
                headers_list.append((b"set-cookie", cookie_value.encode("latin-1")))
                message = dict(message, headers=headers_list)
            await send(message)

        # Restore live components cached from a previous render in this worker
        # (needed for backends that serialise sessions, e.g. RedisBackend).
        _hydrate_component_registry(session)

        try:
            await self.app(scope, receive, send_with_cookie)
        finally:
            if session._dirty:
                await backend.save_session(session)
                session.clear_dirty()
            # Cache live components for SSE rendering with serialising
            # backends (no-op when nothing was rendered this request).
            _cache_component_registry(session)
            _clear_current_session()


class UI:
    """UI layer that attaches inguitive to a user-owned FastAPI app.

    The user constructs their own ``FastAPI()`` instance and passes it to
    ``UI(app, ...)``.  The constructor synchronously wires up session
    middleware, the ``/_sse`` endpoint, the ``/static`` mount, and the
    trigger-handler decorator surface.  FastAPI's own constructor surface
    (lifespan, docs URLs, OpenAPI metadata, root path, etc.) stays fully in
    the user's hands — ``UI()`` takes only inguitive-specific parameters.

    Usage::

        from fastapi import FastAPI
        from inguitive import UI

        app = FastAPI()
        ui = UI(app, title="My App", favicon="/static/favicon.ico")
    """

    def __init__(
        self,
        app: FastAPI,
        title: str = "inguitive",
        favicon: str | None = None,
        head: HeadContent = None,
        configure_session_middleware: bool = True,
        session_backend: SessionBackend | None = None,
        session_cookie_name: str = "inguitive_session_id",
        session_cookie_max_age: int = 3600,
        session_cookie_secure: bool = False,
        session_cookie_httponly: bool = True,
        session_cleanup_interval: int = 100,
        dev_mode: bool = True,
    ):
        """Attach inguitive's UI layer to *app*.

        ``UI`` wires up page-rendering defaults, the ``/_sse`` endpoint, and
        the ``/static`` mount.  By default it also adds
        :class:`SessionMiddleware` to *app*, because SessionState, SSE, and
        OOB re-rendering all require a bound session.  Set
        ``configure_session_middleware=False`` to opt out and add
        ``SessionMiddleware`` yourself (e.g. to control middleware ordering
        or swap the session source).  When opted out, inguitive raises a
        loud, actionable error on the first request if the middleware is
        missing — see :func:`_require_current_session`.

        Args:
            app: The user's FastAPI application instance.
            title: Default ``<title>`` for all pages. Overridden per-page
                via ``ui.page(..., title=...)``.
            favicon: Default favicon path. Defaults to the bundled
                ``/static/inguitive_favicon.svg``.
            head: Default head content (components and/or raw HTML strings)
                appended to every page's ``<head>``.
            configure_session_middleware: When True (default), add
                :class:`SessionMiddleware` to *app* automatically.  When
                False, the user must add it themselves.
            session_backend: Session backend (defaults to ``MemoryBackend``).
                Only used when ``configure_session_middleware`` is True.
            session_cookie_name: Name of the session cookie.
            session_cookie_max_age: Cookie max age in seconds.
            session_cookie_secure: Whether cookie is secure (HTTPS only).
            session_cookie_httponly: Whether cookie is HTTP-only.
            session_cleanup_interval: Call ``cleanup_expired()`` every N requests.
            dev_mode: Enable development mode warnings (default True).
        """
        self.app = app

        # Store defaults on app.state so existing _register_page_route and
        # _render_page_shell can read them with no changes.
        app.state.title = title
        app.state.favicon = favicon
        app.state.head = head
        app.state.dev_mode = dev_mode
        app.state.trigger_handlers = {}
        app.state.page_routes = {}

        # Dev mode warnings
        if dev_mode:
            from inguitive.state import enable_dev_mode_warnings

            enable_dev_mode_warnings()
        else:
            from inguitive.state import disable_dev_mode_warnings

            disable_dev_mode_warnings()

        # Session middleware — added by default, opt-out via flag.
        if configure_session_middleware:
            if session_backend is not None:
                set_session_backend(session_backend)
            app.add_middleware(
                SessionMiddleware,
                session_cookie_name=session_cookie_name,
                session_cookie_max_age=session_cookie_max_age,
                session_cookie_secure=session_cookie_secure,
                session_cookie_httponly=session_cookie_httponly,
                cleanup_interval=session_cleanup_interval,
            )
        else:
            # User opted out — they must add SessionMiddleware themselves.
            # Register a startup check that inspects app.user_middleware and
            # raises a loud, actionable error if they forgot.  (When the user
            # uses a `lifespan` context manager instead of `on_event`, this
            # handler is skipped — the request-time _require_current_session()
            # backstop in ui.page()/trigger routes still catches it.)
            self._register_session_middleware_check(app)

        # Static files mount
        self._mount_static(app)

        # SSE endpoint
        self._register_sse_route(app)

    def _register_session_middleware_check(self, app: FastAPI) -> None:
        """Register a startup handler that verifies SessionMiddleware is present.

        Only used when ``configure_session_middleware=False``.  By startup
        time, all ``add_middleware`` calls have happened, so we can inspect
        ``app.user_middleware`` and fail fast if the user forgot.

        Uses ``on_event("startup")`` rather than a ``lifespan`` context manager
        because ``lifespan`` is singular — setting one would override the
        user's.  ``on_event`` is additive: multiple handlers coexist.
        When the user uses a ``lifespan`` context manager instead of
        ``on_event``, this handler is skipped — the request-time
        ``_require_current_session()`` backstop in ``ui.page()`` and trigger
        routes still catches it.
        """

        @app.on_event("startup")
        def _check_session_middleware() -> None:
            # Check for SessionMiddleware in app.user_middleware.
            # This handles both:
            # 1. Direct SessionMiddleware instances (cls is the class itself)
            # 2. Subclasses of SessionMiddleware (cls is a type, check issubclass)
            has_it = any(
                # m.cls may be a type or a _MiddlewareFactory callable; narrow
                # via a local so isinstance() carries through to issubclass().
                (cls := m.cls) is SessionMiddleware
                or (isinstance(cls, type) and issubclass(cls, SessionMiddleware))
                for m in app.user_middleware
            )
            if not has_it:
                raise RuntimeError(_SESSION_MIDDLEWARE_MISSING_MSG)

    def _mount_static(self, app: FastAPI) -> None:
        """Mount ``/static`` serving user static/ then package static/."""
        static_dirs: list[str] = []

        cwd_static = Path.cwd() / "static"
        if cwd_static.exists() and cwd_static.is_dir():
            static_dirs.append(str(cwd_static))

        pkg_static = Path(str(importlib.resources.files("inguitive"))) / "static"
        if pkg_static.exists() and pkg_static.is_dir():
            static_dirs.append(str(pkg_static))

        if static_dirs:
            from starlette.responses import Response
            from starlette.routing import get_route_path

            async def static_files_app(scope, receive, send):
                if scope["type"] != "http":
                    return
                path = get_route_path(scope).lstrip("/")
                for directory in static_dirs:
                    file_path = Path(directory) / path
                    if file_path.exists() and file_path.is_file():
                        return await FileResponse(str(file_path))(scope, receive, send)
                return await Response(
                    content=b"Not Found",
                    status_code=404,
                    media_type="text/plain",
                )(scope, receive, send)

            app.mount("/static", static_files_app, name="static")
        else:
            warnings.warn(
                "Could not mount static files directory. "
                "The default favicon at '/static/inguitive_favicon.svg' will not be available. "
                "To fix this, either install the package properly or provide a custom favicon "
                "path to UI(app, favicon='...').",
                UserWarning,
                stacklevel=2,
            )

    def _register_sse_route(self, app: FastAPI) -> None:
        """Register the ``GET /_sse`` endpoint."""

        @app.get("/_sse")
        async def _sse_route(request: Request):  # type: ignore[return-value]
            session = _require_current_session()

            session_id = session.session_id
            queue = _register_sse_connection(session_id)

            async def _event_generator():
                loop = asyncio.get_event_loop()

                async def _disconnect_future() -> None:
                    while not await request.is_disconnected():
                        await asyncio.sleep(0.5)

                disconnect_task = loop.create_task(_disconnect_future())
                queue_task: asyncio.Task | None = None

                try:
                    while True:
                        queue_task = loop.create_task(queue.get())
                        done, pending = await asyncio.wait(
                            {queue_task, disconnect_task},
                            timeout=30.0,
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        if disconnect_task in done or not done:
                            if not done:
                                queue_task.cancel()
                                await asyncio.wait({queue_task})
                                yield ": heartbeat\n\n"
                                continue
                            break

                        html: str | None = queue_task.result()
                        if html is None:
                            break
                        lines = "\n".join(f"data: {line}" for line in html.splitlines())
                        yield f"{lines}\n\n"
                except asyncio.CancelledError:
                    pass
                finally:
                    for task in (disconnect_task, queue_task):
                        if task is not None and not task.done():
                            task.cancel()
                            try:
                                await asyncio.wait({task})
                            except (asyncio.CancelledError, Exception):
                                pass
                    _unregister_sse_connection(session_id, queue)

            return StreamingResponse(
                _event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                },
            )

    # ------------------------------------------------------------------
    # Decorator surfaces
    # ------------------------------------------------------------------

    def trigger_handler(self, trigger_name=None):  # type: ignore[no-untyped-def]
        """Register a trigger handler as a POST route at ``/_trigger/<name>``.

        Supports both ``@ui.trigger_handler`` and ``@ui.trigger_handler("name")``.
        """
        return trigger_handler_decorator(self.app, trigger_name)

    def page(
        self,
        component,
        title: str | None = None,
        favicon: str | None = None,
        head: HeadContent = None,
        replace_global_head: bool = False,
    ) -> HTMLResponse:
        """Render *component* inside the HTML document shell and return it.

        Called from inside a plain FastAPI route::

            @app.get("/")
            def home():
                return ui.page(Div(Text("Hello")), title="Home")

        Renders the component via ``.render()``, resolves per-page
        ``title``/``favicon``/``head`` against the ``UI`` defaults stored on
        ``app.state``, merges or replaces ``head`` per ``replace_global_head``,
        and wraps everything in :func:`_render_page_shell`.

        Args:
            component: A :class:`Component` (or anything with a ``.render()``
                method, or a plain string) to render as the page body.
            title: Per-page ``<title>``. Falls back to the UI default, then
                ``"inguitive"``.
            favicon: Per-page favicon path. Falls back to the UI default, then
                the bundled ``/static/inguitive_favicon.svg``.
            head: Per-page head content (components and/or raw HTML strings).
                Merged *after* the UI-level head content unless
                ``replace_global_head`` is True.
            replace_global_head: When False (default), both the UI-level and
                page-level head content are included (UI-level first). When
                True, only the page-level head content is used.
        """
        _require_current_session()

        # Render the component to HTML.
        if hasattr(component, "render") and callable(component.render):
            content = component.render()
        else:
            content = str(component)

        # Resolve effective title/favicon with fallback chain.
        effective_title = title or str(getattr(self.app.state, "title", "inguitive"))
        effective_favicon = (
            favicon
            or getattr(self.app.state, "favicon", None)
            or "/static/inguitive_favicon.svg"
        )

        # Merge or replace head content per replace_global_head.
        if replace_global_head:
            head_sources = [head] if head is not None else []
        else:
            head_sources = []
            app_head = getattr(self.app.state, "head", None)
            if app_head is not None:
                head_sources.append(app_head)
            if head is not None:
                head_sources.append(head)
        head_extra = "".join(_render_template_content(source) for source in head_sources)

        html = _render_page_shell(content, effective_title, effective_favicon, head_extra)
        return HTMLResponse(content=html)
