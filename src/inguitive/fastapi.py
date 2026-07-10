"""
FastAPI integration for INGUITIVE.
"""

from __future__ import annotations

import inspect
import uuid
from pathlib import Path
from typing import Callable, ParamSpec, Protocol, TypeVar, runtime_checkable

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from inguitive.session import (
    Session,
    SessionBackend,
    clear_current_session,
    get_session_backend,
    set_current_session,
    set_session_backend,
)
from inguitive.state import (
    get_mutated_states,
    get_state_by_name,
    track_mutations,
)
from inguitive.htmx import update_components

# Type variables for decorator type annotations
P = ParamSpec("P")
T = TypeVar("T")

# Type aliases for decorator return types
TriggerDecorator = Callable[[Callable[P, T]], Callable[P, T]]
PageDecorator = Callable[[str | None], Callable[[Callable[P, T]], Callable[P, T]]]


@runtime_checkable
class InguitiveApp(Protocol[P, T]):
    """Protocol describing an INGUITIVE application with custom decorators.

    This Protocol extends the FastAPI instance with INGUITIVE-specific decorators.
    Type checkers will recognize these custom attributes on objects of this type.
    """

    # Custom decorators
    trigger_handler: TriggerDecorator[P, T]
    page: PageDecorator[P, T]


def _register_page_route(app, path: str, handler: Callable[P, T]):
    """Helper to register a page route on an app."""

    @app.get(path, response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler):
        sig = inspect.signature(h)
        needs_request = "request" in sig.parameters
        needs_form_data = "form_data" in sig.parameters
        is_async = inspect.iscoroutinefunction(h)

        kwargs = {}
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

        # Wrap in base template
        templates = app.state.templates
        return templates.TemplateResponse(request, "base.html", {"content": content})


def _register_trigger_route(app, trigger_name: str, handler: Callable):
    """Helper to register a trigger route on an app."""

    @app.post(f"/_trigger/{trigger_name.lstrip('/')}", response_class=HTMLResponse)
    async def route_wrapper(request: Request, h=handler, tn=trigger_name):
        sig = inspect.signature(h)
        needs_request = "request" in sig.parameters
        needs_form_data = "form_data" in sig.parameters
        is_async = inspect.iscoroutinefunction(h)

        kwargs = {}
        if needs_request:
            kwargs["request"] = request
        if needs_form_data:
            form_data_dict = dict(await request.form())
            # Merge query parameters (from trigger_args) into form_data
            query_params = dict(request.query_params)
            form_data_dict.update(query_params)
            kwargs["form_data"] = form_data_dict

        # Track state mutations during handler execution for auto-propagation
        with track_mutations():
            result = await h(**kwargs) if is_async else h(**kwargs)

        # If handler returned explicit response, use it (allows overriding auto-propagation)
        if result:
            return result

        # Otherwise, auto-generate OOB response from mutated states
        mutated_state_keys = get_mutated_states()
        all_component_ids = set()
        for state_key in mutated_state_keys:
            # Get the State object for this key and collect its listeners
            state = get_state_by_name(state_key)
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
    ):
        self.app = app
        self.session_cookie_name = session_cookie_name
        self.session_cookie_max_age = session_cookie_max_age
        self.session_cookie_secure = session_cookie_secure
        self.session_cookie_httponly = session_cookie_httponly

    async def __call__(self, scope, receive, send):
        """Process ASGI request with session management."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

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
            session = backend.get_session(session_id)
            if session is None:
                session = Session(session_id=session_id)
                backend.save_session(session)
        else:
            session = Session(session_id=str(uuid.uuid4()))
            backend.save_session(session)

        set_current_session(session)

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

        try:
            await self.app(scope, receive, send_with_cookie)
        finally:
            backend.save_session(session)
            clear_current_session()


def create_app(
    template_dir: str | Path = "templates",
    session_backend: SessionBackend | None = None,
    session_cookie_name: str = "inguitive_session_id",
    session_cookie_max_age: int = 3600,
    session_cookie_secure: bool = False,
    session_cookie_httponly: bool = True,
) -> tuple[InguitiveApp[P, T], Jinja2Templates]:
    """Create and configure a FastAPI application for INGUITIVE.

    Args:
        template_dir: Directory containing Jinja2 templates
        session_backend: Session backend to use (defaults to MemoryBackend)
        session_cookie_name: Name of the session cookie
        session_cookie_max_age: Cookie max age in seconds
        session_cookie_secure: Whether cookie is secure (HTTPS only)
        session_cookie_httponly: Whether cookie is HTTP-only

    Returns:
        Tuple of (InguitiveApp, Jinja2Templates) - the app has custom decorators
        trigger_handler and page for defining handlers and routes
    """
    app = FastAPI()
    templates = Jinja2Templates(directory=template_dir)
    app.state.templates = templates

    # Initialize per-app storage for handlers
    app.state.trigger_handlers = {}
    app.state.page_routes = {}

    # Add app-scoped decorator methods
    def _page_decorator(path: str | None = None):
        def decorator(func: Callable):
            actual_path = path if path is not None else "/"
            app.state.page_routes[actual_path] = func
            _register_page_route(app, actual_path, func)
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

    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        session_cookie_name=session_cookie_name,
        session_cookie_max_age=session_cookie_max_age,
        session_cookie_secure=session_cookie_secure,
        session_cookie_httponly=session_cookie_httponly,
    )

    return app, templates


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


def redirect(url: str, status_code: int = 302):
    """Perform an HTTP redirect to the specified URL.

    Args:
        url: The URL to redirect to
        status_code: HTTP status code (302 for temporary redirect, 301 for permanent)

    Returns:
        RedirectResponse: FastAPI redirect response
    """
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=url, status_code=status_code)
