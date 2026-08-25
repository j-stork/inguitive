"""
FastAPI integration for inguitive.
"""

from __future__ import annotations

import asyncio
import contextvars
import importlib.resources
import inspect
import traceback
import uuid
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec, Protocol, TypeVar, runtime_checkable

import markupsafe
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from jinja2 import BaseLoader, ChoiceLoader, FileSystemLoader, PackageLoader

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
    _get_state_by_name,
    _track_mutations,
)
from inguitive.trigger import _trigger_args_context

# Type variables for decorator type annotations
_P = ParamSpec("_P")
_T = TypeVar("_T")

# Type alias for head content (supports strings, Components, Markup, lists, or None)
HeadContent = str | Component | markupsafe.Markup | list[str | Component | markupsafe.Markup] | None

# Type aliases for decorator return types
_TriggerDecorator = Callable[[Callable[_P, _T]], Callable[_P, _T]]
_PageDecorator = Callable[
    [str | None, str | None, str | None, HeadContent], Callable[[Callable[_P, _T]], Callable[_P, _T]]
]


# Supported path parameter types and their converters
_PATH_PARAM_CONVERTERS: dict[str, Callable[[str], Any]] = {
    "str": lambda x: x,
    "int": lambda x: int(x),
    "float": lambda x: float(x),
    "bool": lambda x: x.lower() in {"true", "1", "yes", "on"},
    "path": lambda x: x,
    "uuid": lambda x: uuid.UUID(x),
}


def _convert_path_param(value: str, type_name: str) -> Any:
    """Convert and validate a path parameter based on its declared type.

    Args:
        value: The raw string value from the URL
        type_name: The declared type (str, int, float, bool, path, uuid)

    Returns:
        Converted value of the appropriate type

    Raises:
        ValueError: If conversion fails (handled by FastAPI as 400)
    """
    # Handle unknown types by treating them as str
    if type_name not in _PATH_PARAM_CONVERTERS:
        type_name = "str"

    converter = _PATH_PARAM_CONVERTERS[type_name]
    return converter(value)


def _parse_path_pattern(path: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse Inguitive path pattern and convert to FastAPI format.

    Args:
        path: Path string with optional <name:type> patterns

    Returns:
        Tuple of (fastapi_compatible_path, list_of_(param_name, param_type))

    Example:
        _parse_path_pattern("/user/<username:str>/<id:int>")
        # Returns: ("/user/{username}/{id}", [("username", "str"), ("id", "int")])
    """
    import re

    # Regex to match <name:type> or <name> patterns
    pattern = r'<([a-zA-Z_][a-zA-Z0-9_]*)(?:\:([a-zA-Z_][a-zA-Z0-9_]*))?>'

    fastapi_path = path
    params = []

    # Find all parameter patterns and replace them
    for match in re.finditer(pattern, path):
        param_name = match.group(1)
        param_type = match.group(2) if match.group(2) else "str"

        # Prevent use of reserved parameter names
        if param_name in ("request", "form_data"):
            raise ValueError(
                f"Path parameter name '{param_name}' is reserved and cannot be used. "
                f"These names are used for FastAPI request injection."
            )

        # Validate that type names don't start with underscore
        if param_type and param_type.startswith("_"):
            raise ValueError(
                f"Path parameter type '{param_type}' is invalid. "
                f"Type names cannot start with underscore."
            )

        params.append((param_name, param_type))
        # Replace the <name:type> with {name} or {name:path} for path type
        if param_type == "path":
            replacement = "{" + param_name + ":path}"
        else:
            replacement = "{" + param_name + "}"
        fastapi_path = fastapi_path.replace(match.group(0), replacement, 1)

    return fastapi_path, params


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
    # Parse path pattern to extract path parameters
    fastapi_path, path_params = _parse_path_pattern(path)

    # Store path parameter metadata on the handler for use in the wrapper
    handler._inguitive_path_params = path_params  # type: ignore

    @app.get(fastapi_path, response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler, pt=page_title, pf=page_favicon, ph=page_head):
        sig = inspect.signature(h)
        needs_request = "request" in sig.parameters
        needs_form_data = "form_data" in sig.parameters
        is_async = inspect.iscoroutinefunction(h)

        kwargs: dict[str, Any] = {}

        # Extract and convert path parameters first (they take precedence)
        path_params_meta = getattr(h, '_inguitive_path_params', [])
        path_params_dict = dict(request.path_params)

        for param_name, param_type in path_params_meta:
            if param_name in path_params_dict:
                raw_value = path_params_dict[param_name]
                try:
                    converted_value = _convert_path_param(raw_value, param_type)
                    kwargs[param_name] = converted_value
                except (ValueError, TypeError) as e:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid {param_name}: {e}"
                    )

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

        # Wrap in base template with title and favicon
        templates = app.state.templates
        return templates.TemplateResponse(
            request,
            "base.html",
            {"content": content, "title": effective_title, "favicon": effective_favicon, "head_extra": head_extra},
        )


def _register_trigger_route(app, trigger_name: str, handler: Callable):
    """Helper to register a trigger route on an app."""

    @app.post(f"/_trigger/{trigger_name.lstrip('/')}", response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler, tn=trigger_name):
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
                mutated_state_keys = _get_mutated_states()
                all_component_ids: set[str] = set()
                for state_key in mutated_state_keys:
                    # Get the State object for this key and collect its listeners
                    state = _get_state_by_name(state_key)
                    if state is not None:
                        all_component_ids.update(state.listeners)

                return update_components(*all_component_ids)


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


def _create_template_loader(template_dir: str | Path = "templates") -> ChoiceLoader:
    """Create a template loader that supports both local and bundled templates.

    Local templates (specified via template_dir) take precedence over bundled templates.
    This allows users to customize templates while falling back to package defaults.

    Args:
        template_dir: Directory containing Jinja2 templates (local path)

    Returns:
        ChoiceLoader: A Jinja2 loader that checks local directory first, then bundled templates
    """
    # Convert to Path if it's a string
    template_path = Path(template_dir) if isinstance(template_dir, str) else template_dir

    # Create list of loaders - local first, then bundled
    loaders: list[BaseLoader] = []

    # Add FileSystemLoader for local templates if directory exists
    if template_path.exists() and template_path.is_dir():
        loaders.append(FileSystemLoader(str(template_path)))

    # Add PackageLoader for bundled templates from the inguitive package
    # We try to add it unconditionally - if the package isn't installed or templates don't exist,
    # Jinja2 will skip this loader when templates aren't found
    try:
        # Check if we can access the templates as a package resource
        # This will work if inguitive is installed (even in editable mode)
        importlib.resources.files("inguitive")
        # If we get here, the package exists, so we can add the PackageLoader
        loaders.append(PackageLoader("inguitive", "templates"))
    except (ImportError, ModuleNotFoundError, AttributeError):
        # Package not installed or not accessible - skip bundled templates
        pass

    # If no loaders were added, use a default FileSystemLoader
    if not loaders:
        loaders.append(FileSystemLoader("templates"))

    # ChoiceLoader tries loaders in order, so local templates override bundled ones
    return ChoiceLoader(loaders)


def _dev_error_handler(request: Request, exc: Exception) -> HTMLResponse:
    """Exception handler that returns a styled error page.

    In dev mode (dev_mode=True), displays full traceback.
    In production mode (dev_mode=False), displays a simple error message.

    Args:
        request: The FastAPI request object
        exc: The exception that was raised

    Returns:
        TemplateResponse with the error page template, status_code=500
    """

    templates: Jinja2Templates = request.app.state.templates
    dev_mode = getattr(request.app.state, "dev_mode", False)
    # Use format_exception to get the full traceback for the given exception
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "dev_mode": dev_mode,
            "traceback": tb,
            "request_url": str(request.url),
            "request_method": request.method,
        },
        status_code=500,
    )


def create_app(
    template_dir: str | Path = "templates",
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
) -> InguitiveApp[_P, _T]:
    """Create and configure a FastAPI application for inguitive.

    Args:
        template_dir: Directory containing Jinja2 templates. If the directory exists,
            it will be used first. If not found, bundled templates from the inguitive
            package will be used as a fallback. This allows for template customization
            while providing defaults out of the box.
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
        (trigger_handler and page) and templates accessible via app.state.templates
    """
    app = FastAPI()
    loader = _create_template_loader(template_dir)
    # Create Jinja2 environment with our custom loader
    from jinja2 import Environment

    env = Environment(loader=loader)
    templates = Jinja2Templates(env=env)
    app.state.templates = templates

    # Store dev_mode on app state for exception handler access
    app.state.dev_mode = dev_mode

    # Set the default title for pages
    app.state.title = title

    # Set the default favicon for pages
    app.state.favicon = favicon

    # Set the default head content for pages
    app.state.head = head

    # Register exception handler for styled error pages
    app.add_exception_handler(Exception, _dev_error_handler)

    # Initialize per-app storage for handlers
    app.state.trigger_handlers = {}
    app.state.page_routes = {}

    # Add app-scoped decorator methods
    def _page_decorator(
        path: str | None = None,
        title: str | None = None,
        favicon: str | None = None,
        head: HeadContent = None,
    ):
        def decorator(func: Callable):
            actual_path = path if path is not None else "/"
            app.state.page_routes[actual_path] = func
            _register_page_route(app, actual_path, func, title, favicon, head)
            return func

        return decorator

    def _trigger_decorator(trigger_name: str | None | Callable = None):
        if callable(trigger_name):
            # Called as @app.trigger_handler (without parentheses)
            # trigger_name is actually the function
            func = trigger_name
            actual_trigger_name = func.__name__
            app.state.trigger_handlers[actual_trigger_name] = func
            _register_trigger_route(app, actual_trigger_name, func)
            return func
        else:
            # Called as @app.trigger_handler("name") (with parentheses)
            # trigger_name is the name string
            def decorator(func: Callable):
                actual_trigger_name = trigger_name or func.__name__
                app.state.trigger_handlers[actual_trigger_name] = func
                _register_trigger_route(app, actual_trigger_name, func)
                return func

            return decorator

    # Attach decorator methods to app
    app.page = _page_decorator  # type: ignore
    app.trigger_handler = _trigger_decorator  # type: ignore

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
        # Create a custom static files app that checks all directories in order
        async def static_files_app(scope, receive, send):
            if scope["type"] != "http":
                return

            path = scope["path"].lstrip("/")
            for directory in static_dirs:
                file_path = Path(directory) / path
                if file_path.exists() and file_path.is_file():
                    return FileResponse(str(file_path))

            # If no file found, return 404
            from starlette.responses import Response
            return Response(
                content=b"Not Found",
                status_code=404,
                media_type="text/plain"
            )

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
                        queue_task.cancel()
                        if not done:
                            # Timeout — send keep-alive and loop.
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
                disconnect_task.cancel()
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
    """
    queues = _get_sse_queues(session_id)
    if not queues:
        return  # Session has no active SSE connections — nothing to do.

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
