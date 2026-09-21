"""
Trigger argument context management for inguitive framework.

Provides context-local storage for trigger_args passed from Components to trigger handlers,
allowing handlers to access these arguments without requiring form_data or request parameters.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from fastapi import Request

# Context variable to store trigger_args for current request
_trigger_args_var: ContextVar[dict[str, str]] = ContextVar(
    "trigger_args",
    default={},
)


def get_trigger_args() -> dict[str, str]:
    """Get trigger_args dictionary for the current trigger handler execution.

    Returns the dictionary of trigger arguments that were passed via Component's
    trigger_args parameter. Returns an empty dict if no trigger_args were passed
    or if called outside of a trigger handler context.

    Example:
        @ui.trigger_handler
        def my_handler():
            args = get_trigger_args()
            column = args.get("column")

    Returns:
        Dict[str, str]: The trigger arguments dictionary.
    """
    return _trigger_args_var.get()


async def get_form_data(request: Request) -> dict[str, str]:
    """Return the posted form fields as a ``dict[str, str]``.

    A thin convenience wrapper around ``await request.form()`` so handlers do
    not have to write ``dict(await request.form())`` themselves. The handler
    must declare a ``request: Request`` parameter (FastAPI injects it) and call
    this helper explicitly:

    Example:
        @ui.trigger_handler
        async def submit(request: Request):
            data = await get_form_data(request)
            name = data.get("name")

    Args:
        request: The FastAPI ``Request`` object (declared as a handler parameter).

    Returns:
        Dict[str, str]: The posted form fields. Checkboxes that are unchecked do
        not appear in the dict (HTML omits them), so use ``data.get("field", default)``
        rather than ``data["field"]`` for optional fields.
    """
    return dict(await request.form())


@contextmanager
def _trigger_args_context(args: dict[str, str]):
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
