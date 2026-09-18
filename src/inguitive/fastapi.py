"""
FastAPI integration for inguitive.
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import importlib.resources
import inspect
import uuid
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec, Protocol, TypeVar, runtime_checkable

import markupsafe
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from inguitive.components import Component
from inguitive.htmx import update_components
from inguitive.session import (
    Session,
    SessionBackend,
    _cache_component_registry,
    _clear_current_session,
    _get_current_session_from_context,
    _get_sse_queues,
    _hydrate_component_registry,
    _put_bounded,
    _register_sse_connection,
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

# Type variables for decorator type annotations
_P = ParamSpec("_P")
_T = TypeVar("_T")

# Type alias for head content (supports strings, Components, Markup, lists, or None)
HeadContent = str | Component | markupsafe.Markup | list[str | Component | markupsafe.Markup] | None

# Protocols for the decorator surfaces bound onto an app in create_app().
#
# Modelled as Protocols (not Callable aliases) so _PageDecorator can expose its
# keyword arguments with defaults: a plain Callable[[A, B, C, D], R] alias has
# no way to express optional arguments, which mypy reports as "Too few
# arguments" at every @app.page("/path") call site. A Protocol's __call__
# signature carries the defaults just like a real function.
class _TriggerDecorator(Protocol[_P, _T]):
    def __call__(self, handler: Callable[_P, _T]) -> Callable[_P, _T]: ...


class _PageDecorator(Protocol[_P, _T]):
    def __call__(
        self,
        path: str | None = None,
        title: str | None = None,
        favicon: str | None = None,
        head: HeadContent = None,
    ) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...


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


@runtime_checkable
class InguitiveApp(Protocol[_P, _T]):
    """Protocol describing an inguitive application with custom decorators.

    This Protocol extends the FastAPI instance with inguitive-specific decorators.
    Type checkers will recognize these custom attributes on objects of this type.
    """

    # Custom decorators
    trigger_handler: _TriggerDecorator[_P, _T]
    page: _PageDecorator[_P, _T]

    # FastAPI event hook used by background-task patterns (e.g. the SSE
    # startup task in sse_global_app.py). Declared here because the Protocol
    # otherwise narrows FastAPI away to just the inguitive decorators; the
    # real FastAPI instance provides this method.
    def on_event(self, event_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


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


def _register_page_route(
    app,
    path: str,
    handler: Callable[_P, _T],
    page_title: str | None = None,
    page_favicon: str | None = None,
    page_head: HeadContent = None,
):
    """Helper to register a page route on an app.

    Args:
        app: The FastAPI application
        path: The URL path for the route
        handler: The handler function to call
        page_title: Optional page-specific title. Falls back to app.state.title or "inguitive"
        page_favicon: Optional page-specific favicon. Falls back to app.state.favicon or default
        page_head: Optional page-specific head content. Can be a string, Component, or list of both.
            This is appended AFTER app-level head content (from create_app).
    """
    # Path is passed directly to FastAPI, which handles {param} syntax natively.
    @app.get(path, response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler, pt=page_title, pf=page_favicon, ph=page_head):
        _require_session_context()
        sig = inspect.signature(h)
        needs_request = "request" in sig.parameters
        needs_form_data = "form_data" in sig.parameters
        is_async = inspect.iscoroutinefunction(h)

        kwargs: dict[str, Any] = {}

        # Pass FastAPI path parameters through to the handler as keyword arguments.
        path_params_dict = dict(request.path_params)
        handler_params = sig.parameters
        for param_name in path_params_dict:
            if param_name in handler_params:
                kwargs[param_name] = path_params_dict[param_name]

        # Add request and form_data if the handler needs them
        if needs_request:
            kwargs["request"] = request
        if needs_form_data:
            form_data_dict = dict(await request.form())
            kwargs["form_data"] = form_data_dict

        result = await h(**kwargs) if is_async else h(**kwargs)

        # If result is a Response object (e.g., RedirectResponse), return it directly
        from starlette.responses import Response

        if isinstance(result, Response):
            return result

        # Auto-render Components if they have a render method
        if hasattr(result, "render") and callable(result.render):
            content = result.render()
        else:
            content = str(result)

        # Resolve effective title with fallback chain:
        # 1. Page-level title (from decorator)
        # 2. App-level title (from create_app)
        # 3. Default title
        effective_title = pt or getattr(app.state, "title", "inguitive")

        # Resolve effective favicon with fallback chain:
        # 1. Page-level favicon (from decorator)
        # 2. App-level favicon (from create_app)
        # 3. Default favicon
        effective_favicon = pf or getattr(app.state, "favicon", None) or "/static/inguitive_favicon.svg"

        # Collect all head content sources in order: app-level first, then page-level
        head_sources = []
        app_head = getattr(app.state, "head", None)
        if app_head is not None:
            head_sources.append(app_head)
        if ph is not None:
            head_sources.append(ph)
        # Render and concatenate all sources
        head_extra = "".join(_render_template_content(source) for source in head_sources)

        # Wrap in the HTML document shell
        html = _render_page_shell(content, effective_title, effective_favicon, head_extra)
        return HTMLResponse(content=html)


def _register_trigger_route(app, trigger_name: str, handler: Callable):
    """Helper to register a trigger route on an app."""

    @app.post(f"/_trigger/{trigger_name.lstrip('/')}", response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler, tn=trigger_name):
        _require_session_context()
        sig = inspect.signature(h)
        needs_request = "request" in sig.parameters
        needs_form_data = "form_data" in sig.parameters
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
                if needs_form_data:
                    form_data_dict = dict(await request.form())
                    # Merge query parameters (from trigger_args) into form_data
                    form_data_dict.update(query_params)
                    kwargs["form_data"] = form_data_dict

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


def page_decorator(
    app,
    path: str | None = None,
    title: str | None = None,
    favicon: str | None = None,
    head: HeadContent = None,
):
    """Register a page handler at ``path`` and expose it as a route.

    Bound onto a FastAPI app instance in :func:`create_app` as ``app.page``
    (via :func:`functools.partial`), so user code writes ``@app.page("/")``.

    The decorated function is stored in ``app.state.page_routes`` and
    registered as a real FastAPI GET route through
    :func:`_register_page_route`. The handler may declare ``request``,
    ``form_data``, and any path parameters as parameters; these are
    injected at request time.

    Args:
        app: The FastAPI application to register the route on. Bound
            automatically when attached as ``app.page``, so users never
            pass it.
        path: URL path for the route. Supports ``{name}`` path parameters
            (e.g. ``"/items/{item_id}"``). Defaults to ``"/"`` when None.
        title: Optional page-specific ``<title>``. Falls back to the
            app-level title from ``create_app(title=...)``, then to
            ``"inguitive"``.
        favicon: Optional page-specific favicon path. Falls back to the
            app-level favicon, then the bundled
            ``/static/inguitive_favicon.svg``.
        head: Optional page-specific head content (string, Component, or
            list). Appended *after* any app-level head content.

    Returns:
        A decorator that registers ``func`` and returns it unchanged.

    Usage:
        @app.page("/")
        def home():
            return Div(Text("Hello"))
    """
    def decorator(func: Callable):
        actual_path = path if path is not None else "/"
        app.state.page_routes[actual_path] = func
        _register_page_route(app, actual_path, func, title, favicon, head)
        return func

    return decorator


def trigger_handler_decorator(app, trigger_name: str | None | Callable = None):
    """Register a trigger handler callable, exposed as ``app.trigger_handler``.

    Bound onto a FastAPI app instance in :func:`create_app` as
    ``app.trigger_handler`` (via :func:`functools.partial`). Supports two
    call styles:

    - ``@app.trigger_handler`` (no parentheses): the handler is registered
      under its own function name.
    - ``@app.trigger_handler("name")`` (with parentheses): the handler is
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


_SESSION_MIDDLEWARE_MISSING_MSG = (
    "inguitive's SessionMiddleware is not configured on this app. "
    "SessionState, SSE, and OOB component re-rendering all require a "
    "bound session. Either pass configure_session_middleware=True (the "
    "default) to UI(...), or add it yourself:\n"
    "\n"
    "    from inguitive import SessionMiddleware\n"
    "    app.add_middleware(SessionMiddleware)\n"
    "\n"
    "If you set configure_session_middleware=False on UI(...), you must "
    "add this line yourself."
)


def _require_session_context() -> None:
    """Raise a loud, actionable error if no session is bound to the context.

    Fires when SessionMiddleware has not run for this request — i.e. the user
    set ``configure_session_middleware=False`` on ``UI(...)`` and forgot to
    ``app.add_middleware(SessionMiddleware)`` themselves.  Without a bound
    session, SessionState, SSE, and OOB re-rendering silently degrade; this
    turns that silent failure into an immediate, explained error.
    """
    if _get_current_session_from_context() is None:
        raise RuntimeError(_SESSION_MIDDLEWARE_MISSING_MSG)


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
        missing — see :func:`_require_session_context`.

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

        # Static files mount
        self._mount_static(app)

        # SSE endpoint
        self._register_sse_route(app)

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
            _require_session_context()
            session = _get_current_session_from_context()
            assert session is not None  # _require_session_context guarantees this

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
        path: str | None = None,
        title: str | None = None,
        favicon: str | None = None,
        head: HeadContent = None,
    ):
        """Register a page route at *path* that returns ``ui.page(...)`` content.

        This is the ``@ui.page("/path")`` decorator.  It wraps the handler
        in the HTML document shell, resolving title/favicon/head against
        the ``UI`` defaults.
        """
        def decorator(handler: Callable):
            actual_path = path or "/"
            _register_page_route(
                self.app, actual_path, handler,
                page_title=title, page_favicon=favicon, page_head=head,
            )
            return handler

        return decorator


def create_app(
    title: str = "inguitive",
    favicon: str | None = None,
    head: HeadContent = None,
    session_backend: SessionBackend | None = None,
    session_cookie_name: str = "inguitive_session_id",
    session_cookie_max_age: int = 3600,
    session_cookie_secure: bool = False,
    session_cookie_httponly: bool = True,
    session_cleanup_interval: int = 100,
    dev_mode: bool = True,
) -> InguitiveApp[Any, Any]:
    """Create and configure a FastAPI application for inguitive.

    Args:
        title: Default title for pages. Can be overridden per-page via the @app.page decorator.
            Defaults to "inguitive".
        favicon: Default favicon path for pages. Can be overridden per-page via the @app.page
            decorator. Can be a URL path (e.g. /static/favicon.ico) or an absolute URL (e.g. https://...).
            Defaults to None, which uses the bundled INGUITIVE favicon at /static/inguitive_favicon.svg.
        head: Default head content for pages (e.g., CSS, JS, meta tags). This content is
            applied to ALL pages and can be a string, Component, or list of both. Page-level
            head content (via @app.page decorator) is appended AFTER app-level content,
            allowing app-wide resources to load first followed by page-specific additions.
            Defaults to None (empty).
        session_backend: Session backend to use (defaults to MemoryBackend)
        session_cookie_name: Name of the session cookie
        session_cookie_max_age: Cookie max age in seconds
        session_cookie_secure: Whether cookie is secure (HTTPS only)
        session_cookie_httponly: Whether cookie is HTTP-only
        session_cleanup_interval: Call cleanup_expired() every N requests (default: 100)
        dev_mode: Enable development mode warnings (default: True). Set to False in production
            to disable warnings about state mutations with no listeners.

    Returns:
        InguitiveApp - the FastAPI application with inguitive decorators
        (trigger_handler and page)
    """
    app = FastAPI()

    # Store dev_mode on app state
    app.state.dev_mode = dev_mode

    # Set the default title for pages
    app.state.title = title

    # Set the default favicon for pages
    app.state.favicon = favicon

    # Set the default head content for pages
    app.state.head = head

    # Initialize per-app storage for handlers
    app.state.trigger_handlers = {}
    app.state.page_routes = {}

    # Attach app-scoped decorator methods. The actual logic lives in the
    # module-level page_decorator / trigger_handler_decorator functions so
    # they are statically discoverable (e.g. by gather_package_documentation);
    # functools.partial binds `app` so user code calls @app.page(...) and
    # @app.trigger_handler exactly as before.
    app.page = functools.partial(page_decorator, app)  # type: ignore
    app.trigger_handler = functools.partial(trigger_handler_decorator, app)  # type: ignore

    # Configure session backend
    if session_backend is not None:
        set_session_backend(session_backend)

    # Enable or disable dev mode warnings based on dev_mode parameter
    if dev_mode:
        from inguitive.state import enable_dev_mode_warnings

        enable_dev_mode_warnings()
    else:
        from inguitive.state import disable_dev_mode_warnings

        disable_dev_mode_warnings()

    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        session_cookie_name=session_cookie_name,
        session_cookie_max_age=session_cookie_max_age,
        session_cookie_secure=session_cookie_secure,
        session_cookie_httponly=session_cookie_httponly,
        cleanup_interval=session_cleanup_interval,
    )

    # Mount static files - prioritize CWD/static/, then package static/
    static_dirs = []

    # 1. Check CWD/static/ first (user's project static files)
    cwd_static = Path.cwd() / "static"
    if cwd_static.exists() and cwd_static.is_dir():
        static_dirs.append(str(cwd_static))

    # 2. Check package static/ directory (Python 3.10+ guarantees importlib.resources exists)
    pkg_static = Path(str(importlib.resources.files("inguitive"))) / "static"
    if pkg_static.exists() and pkg_static.is_dir():
        static_dirs.append(str(pkg_static))

    if static_dirs:
        # Custom static files app that checks all candidate directories in order.
        #
        # Note on path handling: Starlette's `Mount` does not strip the mount
        # prefix from ``scope["path"]`` for a raw ASGI sub-app. The remainder
        # is exposed via ``scope["root_path"]`` (set to the mount prefix), so we
        # use Starlette's ``get_route_path`` helper which strips ``root_path``
        # from ``scope["path"]`` to recover the path relative to the mount.
        from starlette.responses import Response
        from starlette.routing import get_route_path

        async def static_files_app(scope, receive, send):
            if scope["type"] != "http":
                return

            # Relative path below the mount, e.g. "inguitive_favicon.svg".
            path = get_route_path(scope).lstrip("/")
            for directory in static_dirs:
                file_path = Path(directory) / path
                if file_path.exists() and file_path.is_file():
                    return await FileResponse(str(file_path))(scope, receive, send)

            # No matching file in any directory — return a plain 404.
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
            "path to create_app(favicon='...').",
            UserWarning,
            stacklevel=2,
        )

    # -----------------------------------------------------------------------
    # SSE endpoint — GET /_sse
    # -----------------------------------------------------------------------

    @app.get("/_sse")
    async def _sse_route(request: Request):  # type: ignore[return-value]
        """Persistent SSE stream for server-initiated component updates.

        Every inguitive page connects here automatically via the hidden
        ``#hx-target`` div in ``base.html``.  The session is authenticated
        by the standard session cookie (handled by :class:`SessionMiddleware`).
        """
        session = _get_current_session_from_context()
        if session is None:
            return HTMLResponse("No active session", status_code=401)

        session_id = session.session_id
        queue = _register_sse_connection(session_id)

        async def _event_generator():
            # Wrap is_disconnected() as an asyncio Future so we can race it
            # against queue.get() without blocking on either for 30 seconds.
            loop = asyncio.get_event_loop()

            async def _disconnect_future() -> None:
                while not await request.is_disconnected():
                    await asyncio.sleep(0.5)

            disconnect_task = loop.create_task(_disconnect_future())
            # Track the queue_task across loop iterations so the finally
            # block can cancel and await it even if a CancelledError fires
            # mid-iteration (otherwise it leaks as an orphaned pending task
            # and Python logs "Task was destroyed but it is pending").
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
                        # Client disconnected or heartbeat timeout elapsed.
                        if not done:
                            # Timeout — send keep-alive and loop.  The
                            # queue_task is still pending; cancel and await
                            # it so it does not leak before the next iteration
                            # overwrites queue_task.
                            queue_task.cancel()
                            await asyncio.wait({queue_task})
                            yield ": heartbeat\n\n"
                            continue
                        break

                    # queue_task completed — send the HTML fragment.
                    html: str | None = queue_task.result()
                    if html is None:  # sentinel — close cleanly
                        break
                    lines = "\n".join(f"data: {line}" for line in html.splitlines())
                    yield f"{lines}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                # Cancel and await both tasks so their cancellations settle
                # before the generator returns.  A bare cancel() without
                # awaiting leaves the task pending; Python then destroys it
                # mid-flight and logs "Task was destroyed but it is pending".
                # Awaiting guarantees the task body has unwound, which also
                # frees the SSE stream promptly when the client navigates away.
                for task in (disconnect_task, queue_task):
                    if task is not None and not task.done():
                        task.cancel()
                        try:
                            await asyncio.wait({task})
                        except (asyncio.CancelledError, Exception):
                            pass
                # Remove only this tab's queue; other tabs are unaffected.
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

    return app  # type: ignore[return-value]


async def push_update(session_id: str, *component_ids: str) -> None:
    """Push OOB HTML for specific components to a session's SSE stream.

    Use this for fine-grained, per-session pushes from background tasks or
    webhook handlers.  For a broadcast push to *all* connected sessions, call
    :meth:`State.set` from outside a request context instead.

    Args:
        session_id: The session to push to.  Obtain it from
            :func:`~inguitive.session.get_session_id` during a request and
            store it for later use.
        *component_ids: IDs of the components to re-render as OOB swaps.
            The components must already be registered in the session's
            component registry (i.e. they must have been rendered at least
            once when the page loaded).

    Example::

        from inguitive import push_update, get_session_id

        # Inside a request handler — capture the session ID:
        current_session = get_session_id()

        # Later, in a background task:
        async def notify():
            await push_update(current_session, "notification-banner")

    When called from within a ``session_context`` block for the same session,
    component IDs can be resolved the same way as ``update_components``::

        async with session_context(session_id) as session:
            if session is None:
                return
            counter_state.set(counter_state.get() + 1)
            await push_update(session_id, *counter_state.listeners)
    """
    queues = _get_sse_queues(session_id)
    if not queues:
        return  # Session has no active SSE connections — nothing to do.

    # If the target session is the one currently bound in this context (e.g.
    # push_update called from within a session_context block), use it directly
    # rather than reloading from the backend. This sees in-flight mutations
    # that have not yet been persisted (the save happens at context exit) and
    # avoids a stale-copy read on serialising backends such as RedisBackend.
    session = _get_current_session_from_context()
    if session is None or session.session_id != session_id:
        backend = get_session_backend()
        session = await backend.get_session(session_id)
        if session is None:
            return
        # Rendering requires a populated component_registry.  MemoryBackend
        # returns the live session; for serialising backends (RedisBackend) the
        # registry is restored from the worker's process-local component cache.
        _hydrate_component_registry(session)

    def _render(s=session, ids=component_ids) -> str:
        _set_current_session(s)
        return update_components(*ids)

    html = contextvars.copy_context().run(_render)
    if html:
        # Fan out to every open tab for this session.
        # _put_bounded is non-blocking and applies drop-oldest backpressure.
        for queue in list(queues):  # snapshot to avoid mutation during iteration
            _put_bounded(queue, html)


def run_app(app_module: str = "app:app", host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Run the FastAPI application using Uvicorn.

    Args:
        app_module: Uvicorn app module string (e.g., "app:app")
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload in development
    """
    import uvicorn

    uvicorn.run(app_module, host=host, port=port, reload=reload)


def redirect(url: str, status_code: int = 302) -> Any:
    """Perform an HTTP redirect to the specified URL.

    Args:
        url: The URL to redirect to
        status_code: HTTP status code (302 for temporary redirect, 301 for permanent)

    Returns:
        RedirectResponse: FastAPI redirect response
    """
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=url, status_code=status_code)
