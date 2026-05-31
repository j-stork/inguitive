"""
INGUITIVE - A pure Python web framework combining intuitive syntax with HTMX and Tailwind CSS.
"""

from inguitive.components import Component, Div, Button, Label, Icon, Input, Textarea, Select, Checkbox, Radio, Form, Markdown
from inguitive.state import State
from inguitive.htmx import update_components
from inguitive.fastapi import create_app, run_app

# Re-export styling constants for convenience
from inguitive.css import (
    BUTTON_BASE_CSS,
    BUTTON_PRIMARY_CSS,
    BUTTON_SECONDARY_CSS,
)

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
    # State
    "State",
    # HTMX helpers
    "update_components",
    # FastAPI
    "create_app",
    "run_app",
    # Styling
    "BUTTON_BASE_CSS",
    "BUTTON_PRIMARY_CSS",
    "BUTTON_SECONDARY_CSS",
]

__version__ = "0.1.0"
