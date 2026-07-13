"""
Trigger argument context management for INGUITIVE framework.

Provides context-local storage for trigger_args passed from Components to trigger handlers,
allowing handlers to access these arguments without requiring form_data or request parameters.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict

# Context variable to store trigger_args for current request
_trigger_args_var: ContextVar[Dict[str, str]] = ContextVar(
    "trigger_args",
    default={},
)


def get_trigger_args() -> Dict[str, str]:
    """Get trigger_args dictionary for the current trigger handler execution.

    Returns the dictionary of trigger arguments that were passed via Component's
    trigger_args parameter. Returns an empty dict if no trigger_args were passed
    or if called outside of a trigger handler context.

    Example:
        @app.trigger_handler
        def my_handler():
            args = get_trigger_args()
            column = args.get("column")

    Returns:
        Dict[str, str]: The trigger arguments dictionary.
    """
    return _trigger_args_var.get()


@contextmanager
def trigger_args_context(args: Dict[str, str]):
    """Context manager to temporarily set trigger_args for handler execution.

    This is used internally by the framework to populate trigger_args from URL
    query parameters before calling a trigger handler, and to clean up
    afterwards.

    Args:
        args: Dictionary of trigger argument key-value pairs.
    """
    token = _trigger_args_var.set(args.copy())
    try:
        yield
    finally:
        _trigger_args_var.reset(token)
