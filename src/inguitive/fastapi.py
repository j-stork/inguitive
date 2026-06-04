"""
FastAPI integration for INGUITIVE.
"""

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
    """FastAPI middleware for session management."""
    
    def __init__(self, app: FastAPI, session_cookie_name: str = "inguitive_session_id", 
                 session_cookie_max_age: int = 3600, session_cookie_secure: bool = False,
                 session_cookie_httponly: bool = True):
        """
        Initialize session middleware.
        
        Args:
            app: FastAPI application
            session_cookie_name: Name of the session cookie
            session_cookie_max_age: Cookie max age in seconds
            session_cookie_secure: Whether cookie is secure (HTTPS only)
            session_cookie_httponly: Whether cookie is HTTP-only
        """
        self.app = app
        self.session_cookie_name = session_cookie_name
        self.session_cookie_max_age = session_cookie_max_age
        self.session_cookie_secure = session_cookie_secure
        self.session_cookie_httponly = session_cookie_httponly
    
    async def __call__(self, request: Request, call_next):
        """Process request with session management."""
        # Get session ID from cookie
        session_id = request.cookies.get(self.session_cookie_name)
        backend = get_session_backend()
        
        # Get or create session
        if session_id:
            session = backend.get_session(session_id)
            if session is not None:
                set_current_session(session)
            else:
                # Session not found, create new one
                session = Session(session_id=session_id)
                backend.save_session(session)
                set_current_session(session)
        else:
            # No session cookie, create new session
            session = Session(session_id=str(uuid.uuid4()))
            backend.save_session(session)
            set_current_session(session)
        
        # Process request
        response = await call_next(request)
        
        # Set session cookie
        response.set_cookie(
            key=self.session_cookie_name,
            value=session.session_id,
            max_age=self.session_cookie_max_age,
            secure=self.session_cookie_secure,
            httponly=self.session_cookie_httponly,
            samesite="lax"
        )
        
        # Save session if it was modified
        # In a more sophisticated implementation, we'd track if the session was modified
        backend.save_session(session)
        
        # Clean up context
        clear_current_session()
        
        return response


def create_app(template_dir: str | Path = "templates", 
               session_backend: Optional[SessionBackend] = None,
               session_cookie_name: str = "inguitive_session_id",
               session_cookie_max_age: int = 3600,
               session_cookie_secure: bool = False,
               session_cookie_httponly: bool = True) -> FastAPI:
    """Create and configure a FastAPI application for INGUITIVE.
    
    Args:
        template_dir: Directory containing Jinja2 templates
        session_backend: Session backend to use (defaults to MemoryBackend)
        session_cookie_name: Name of the session cookie
        session_cookie_max_age: Cookie max age in seconds
        session_cookie_secure: Whether cookie is secure (HTTPS only)
        session_cookie_httponly: Whether cookie is HTTP-only
        
    Returns:
        Configured FastAPI app instance
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
    
    return app


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
