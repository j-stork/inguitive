"""
inguitive - A pure Python web framework combining intuitive syntax with HTMX and Tailwind CSS.
"""

from inguitive.components import (
    Button,
    Checkbox,
    Component,
    DataTable,
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

# Re-export SVG icons for convenience
from inguitive.svg import MOON, SUN
from inguitive.trigger import get_trigger_args
from inguitive.utils import nl2br

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
    "DataTable",
    # State
    "State",
    # HTMX helpers
    "update_components",
    # Trigger
    "get_trigger_args",
    # Helpers
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
    # Icons
    "MOON",
    "SUN",
    # Utilities
    "nl2br",
]

__version__ = "0.1.3"
