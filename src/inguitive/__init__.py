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
    Header,
    Icon,
    Image,
    Input,
    Label,
    Link,
    Radio,
    Select,
    TemplateComponent,
    Text,
    Textarea,
)
from inguitive.fastapi import InguitiveApp, create_app, push_update, redirect, run_app
from inguitive.htmx import update_components
from inguitive.session import (
    MemoryBackend,
    RedisBackend,
    Session,
    SessionBackend,
    get_session_backend,
    get_session_id,
    session_context,
    set_session_backend,
)
from inguitive.state import State
from inguitive.trigger import get_trigger_args
from inguitive.utils import nl2br
from inguitive.validation import (
    CustomValidator,
    Field,
    FormSchema,
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
    RequiredValidator,
    ValidationError,
    Validator,
    field,
    validate_form,
)

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
    "Link",
    "Header",
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
    "push_update",
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
    "session_context",
    # Utilities
    "nl2br",
    # Validation
    "Field",
    "FormSchema",
    "ValidationError",
    "Validator",
    "CustomValidator",
    "RequiredValidator",
    "MinLengthValidator",
    "MaxLengthValidator",
    "MinValueValidator",
    "MaxValueValidator",
    "RegexValidator",
    "field",
    "validate_form",
]

__version__ = "0.9.0"
