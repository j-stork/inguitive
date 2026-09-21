"""
inguitive - A pure Python UI layer for FastAPI: compose pages from Python
components instead of templates, with reactive state and SSE-driven partial
updates via HTMX.
"""

from inguitive.components import (
    Anchor,
    Button,
    Checkbox,
    Component,
    DataTable,
    Div,
    Form,
    Header,
    Icon,
    Image,
    Input,
    Label,
    Radio,
    Select,
    TemplateComponent,
    Text,
    Textarea,
)
from inguitive.fastapi import (
    UI,
    SessionMiddleware,
)
from inguitive.htmx import update_components
from inguitive.session import (
    MemoryBackend,
    SessionBackend,
    get_session_backend,
    get_session_id,
    session_active,
    session_context,
    set_session_backend,
)
from inguitive.state import SessionState, State
from inguitive.trigger import get_form_data, get_trigger_args
from inguitive.utils import nl2br

__all__ = [
    # Components
    "Component",
    "Div",
    "Button",
    "Label",
    "Icon",
    "Image",
    "Input",
    "Textarea",
    "Select",
    "Checkbox",
    "Radio",
    "Form",
    "Text",
    "Anchor",
    "Header",
    "TemplateComponent",
    "DataTable",
    # State
    "State",
    "SessionState",
    # HTMX helpers
    "update_components",
    # Trigger
    "get_trigger_args",
    "get_form_data",
    # Helpers
    # FastAPI
    "UI",
    "SessionMiddleware",
    # Session
    "SessionBackend",
    "MemoryBackend",
    "set_session_backend",
    "get_session_backend",
    "get_session_id",
    "session_active",
    "session_context",
    # Utilities
    "nl2br",
]

__version__ = "2.0.0"
