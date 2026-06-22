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
    Markdown,
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
from inguitive.fastapi import create_app, run_app
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
    "Markdown",
    "Text",
    "Link",
    "TemplateComponent",
    # State
    "State",
    # HTMX helpers
    "update_components",
    # FastAPI
    "create_app",
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
