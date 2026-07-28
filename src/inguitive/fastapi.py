"""
FastAPI integration for INGUITIVE.
"""

from __future__ import annotations

import uuid
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Callable, Optional
from pathlib import Path
from inguitive.session import (
    get_session_backend, 
    set_session_backend, 
    SessionBackend, 
    MemoryBackend,
    RedisBackend,
    get_or_create_current_session,
    set_current_session,
    clear_current_session,
    Session,
)


class SessionMiddleware:
    """FastAPI/Starlette ASGI middleware for session management."""
    
    def __init__(self, app, session_cookie_name: str = "inguitive_session_id", 
                 session_cookie_max_age: int = 3600, session_cookie_secure: bool = False,
                 session_cookie_httponly: bool = True):
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

def create_app(template_dir: str | Path = "templates", 
               session_backend: Optional[SessionBackend] = None,
               session_cookie_name: str = "inguitive_session_id",
               session_cookie_max_age: int = 3600,
               session_cookie_secure: bool = False,
               session_cookie_httponly: bool = True):
    """Create and configure a FastAPI application for INGUITIVE.
    
    Args:
        template_dir: Directory containing Jinja2 templates
        session_backend: Session backend to use (defaults to MemoryBackend)
        session_cookie_name: Name of the session cookie
        session_cookie_max_age: Cookie max age in seconds
        session_cookie_secure: Whether cookie is secure (HTTPS only)
        session_cookie_httponly: Whether cookie is HTTP-only
        
    Returns:
        Tuple of (FastAPI app, Jinja2Templates) for use in routes
    """
    app = FastAPI()
    templates = Jinja2Templates(directory=template_dir)
    app.state.templates = templates
    
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
