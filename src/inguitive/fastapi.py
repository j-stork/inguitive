"""
FastAPI integration for INGUITIVE.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Callable
from pathlib import Path

# Re-export styling constants for convenience
from inguitive.css import (
    BUTTON_BASE_CSS,
    BUTTON_PRIMARY_CSS,
    BUTTON_SECONDARY_CSS,
)


def create_app(template_dir: str | Path = "templates") -> FastAPI:
    """Create and configure a FastAPI application for INGUITIVE.
    
    Args:
        template_dir: Directory containing Jinja2 templates
        
    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI()
    templates = Jinja2Templates(directory=template_dir)
    app.state.templates = templates
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
