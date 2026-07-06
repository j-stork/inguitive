"""
INGUITIVE - A pure Python web framework combining intuitive syntax with HTMX and Tailwind CSS.
"""

from inguitive.components import (
    Button,
    Checkbox,
    Component,
    Div,
    Form,
    Icon,
    Input,
    Label,
    Link,
    Radio,
    Select,
    TemplateComponent,
    Text,
    Textarea,
)

# Re-export styling constants for convenience
from inguitive.css import (
    BUTTON_BASE_CSS,
    BUTTON_PRIMARY_CSS,
    BUTTON_SECONDARY_CSS,
)
from inguitive.fastapi import InguitiveApp, create_app, redirect, run_app
from inguitive.htmx import update_components
from inguitive.session import (
    MemoryBackend,
    RedisBackend,
    Session,
    SessionBackend,
    get_session_backend,
    get_session_id,
    set_session_backend,
)
from inguitive.state import State


def dynamic(value):
    """Mark a value as dynamic - re-evaluated on component updates.
    
    Use this to make any expression re-evaluate when the parent component's
    listened-to states change. This is syntactic sugar over lambda that makes
    the intent clearer.
    
    Args:
        value: Any value or expression that should be re-evaluated
        
    Returns:
        A callable that returns the value when invoked
        
    Example:
        # Instead of: lambda: state.get()
        Div(dynamic(state.get()), listen_to="state")
        
        # Instead of: lambda: f"Count: {count}"
        Text(dynamic(f"Count: {count_state.get()}"))
    """
    if callable(value):
        return value
    return lambda: value


__all__ = [
    # Components
    "Component",
    "Div",
    "Button",
    "Label",
    "Icon",
    "Input",
    "Textarea",
    "Select",
    "Checkbox",
    "Radio",
    "Form",
    "Text",
    "Link",
    "TemplateComponent",
    # State
    "State",
    # HTMX helpers
    "update_components",
    # Helpers
    "dynamic",
    # FastAPI
    "InguitiveApp",
    "create_app",
    "redirect",
    "run_app",
    # Session
    "Session",
    "SessionBackend",
    "MemoryBackend",
    "RedisBackend",
    "set_session_backend",
    "get_session_backend",
    "get_session_id",
    # Styling
    "BUTTON_BASE_CSS",
    "BUTTON_PRIMARY_CSS",
    "BUTTON_SECONDARY_CSS",
]

__version__ = "0.1.0"
