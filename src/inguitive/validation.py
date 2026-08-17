"""
Form validation layer for inguitive trigger handlers.

Provides a declarative way to define form schemas with type coercion,
required field validation, custom validators, and structured error messages.

Example usage:
    from inguitive import FormSchema, field, validate_form, ValidationError

    class AddTodoSchema(FormSchema):
        title = field(str, required=True, min_length=1)
        priority = field(int, default=0, min_value=0, max_value=10)
        completed = field(bool, default=False)

    @app.trigger_handler
    @validate_form(AddTodoSchema)
    async def add_todo(form: AddTodoSchema) -> str:
        # form is validated and typed
        return f"Added: {form.title}"
"""

import functools
import inspect
import re
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

# Type variables for decorator type annotations
_P = ParamSpec("_P")
_T = TypeVar("_T")


class ValidationError(Exception):
    """Exception raised when form validation fails.

    Stores field-level errors as a dictionary mapping field names to lists of error messages.
    """

    def __init__(self, errors: dict[str, list[str]]):
        """Initialize ValidationError with field errors.

        Args:
            errors: Dictionary mapping field names to lists of error messages.
                   Example: {"username": ["This field is required"], "email": ["Invalid format"]}
        """
        self.errors = errors
        super().__init__(str(errors))

    def __str__(self) -> str:
        """Return string representation of validation errors."""
        error_messages: list[str] = []
        for field_name, messages in self.errors.items():
            for message in messages:
                error_messages.append(f"{field_name}: {message}")
        if error_messages:
            return "Validation failed: " + "; ".join(error_messages)
        return "Validation failed"

    def __repr__(self) -> str:
        return f"ValidationError({self.errors!r})"

    def first_error(self, field: str | None = None) -> str | None:
        """Get the first error message for a specific field or any field.

        Args:
            field: Field name to get error for. If None, returns first error from any field.

        Returns:
            First error message string, or None if no errors.
        """
        if field is not None:
            errors = self.errors.get(field, [])
            return errors[0] if errors else None

        for messages in self.errors.values():
            if messages:
                return messages[0]
        return None

    def has_errors(self, field: str | None = None) -> bool:
        """Check if there are errors for a specific field or any field.

        Args:
            field: Field name to check. If None, checks if there are any errors.

        Returns:
            True if there are errors, False otherwise.
        """
        if field is not None:
            return field in self.errors and len(self.errors[field]) > 0
        return len(self.errors) > 0


class Validator:
    """Base validator class."""

    def __init__(self, error_message: str | None = None):
        """Initialize validator with optional custom error message.

        Args:
            error_message: Custom error message to use when validation fails.
        """
        self.error_message = error_message

    def validate(self, value: Any) -> str | None:
        """Validate a value.

        Args:
            value: The value to validate.

        Returns:
            Error message string if validation fails, None if valid.
        """
        raise NotImplementedError


class RequiredValidator(Validator):
    """Validator that ensures a field is present and non-empty."""

    def validate(self, value: Any) -> str | None:
        """Check if value is present and non-empty.

        For strings, checks that the value is not None and not empty/whitespace.
        For other types, checks that the value is not None.
        """
        if value is None:
            return self.error_message or "This field is required"
        if isinstance(value, str) and not value.strip():
            return self.error_message or "This field cannot be empty"
        return None


class MinLengthValidator(Validator):
    """Validator that ensures string length is at least a minimum value."""

    def __init__(self, min_length: int, error_message: str | None = None):
        """Initialize with minimum length requirement.

        Args:
            min_length: Minimum required length.
            error_message: Custom error message.
        """
        super().__init__(error_message)
        self.min_length = min_length

    def validate(self, value: Any) -> str | None:
        """Check if string value has at least min_length characters."""
        if value is None or not isinstance(value, str):
            return None
        if len(value) < self.min_length:
            return self.error_message or f"Must be at least {self.min_length} characters"
        return None


class MaxLengthValidator(Validator):
    """Validator that ensures string length is at most a maximum value."""

    def __init__(self, max_length: int, error_message: str | None = None):
        """Initialize with maximum length requirement.

        Args:
            max_length: Maximum allowed length.
            error_message: Custom error message.
        """
        super().__init__(error_message)
        self.max_length = max_length

    def validate(self, value: Any) -> str | None:
        """Check if string value has at most max_length characters."""
        if value is None or not isinstance(value, str):
            return None
        if len(value) > self.max_length:
            return self.error_message or f"Must be at most {self.max_length} characters"
        return None


class MinValueValidator(Validator):
    """Validator that ensures numeric value is at least a minimum value."""

    def __init__(self, min_value: float, error_message: str | None = None):
        """Initialize with minimum value requirement.

        Args:
            min_value: Minimum allowed value.
            error_message: Custom error message.
        """
        super().__init__(error_message)
        self.min_value = min_value

    def validate(self, value: Any) -> str | None:
        """Check if numeric value is at least min_value."""
        if value is None:
            return None
        try:
            if float(value) < self.min_value:
                return self.error_message or f"Must be at least {self.min_value}"
        except (ValueError, TypeError):
            pass
        return None


class MaxValueValidator(Validator):
    """Validator that ensures numeric value is at most a maximum value."""

    def __init__(self, max_value: float, error_message: str | None = None):
        """Initialize with maximum value requirement.

        Args:
            max_value: Maximum allowed value.
            error_message: Custom error message.
        """
        super().__init__(error_message)
        self.max_value = max_value

    def validate(self, value: Any) -> str | None:
        """Check if numeric value is at most max_value."""
        if value is None:
            return None
        try:
            if float(value) > self.max_value:
                return self.error_message or f"Must be at most {self.max_value}"
        except (ValueError, TypeError):
            pass
        return None


class RegexValidator(Validator):
    """Validator that ensures string value matches a regex pattern."""

    def __init__(self, pattern: str, error_message: str | None = None):
        """Initialize with regex pattern.

        Args:
            pattern: Regular expression pattern to match.
            error_message: Custom error message.
        """
        super().__init__(error_message)
        self.pattern = pattern
        self.compiled = re.compile(pattern)

    def validate(self, value: Any) -> str | None:
        """Check if string value matches the regex pattern."""
        if value is None or not isinstance(value, str):
            return None
        if not self.compiled.fullmatch(value):
            return self.error_message or f"Does not match pattern: {self.pattern}"
        return None


class CustomValidator(Validator):
    """Validator that uses a custom validation function."""

    def __init__(self, func: Callable[[Any], bool | str | None], error_message: str | None = None):
        """Initialize with custom validation function.

        Args:
            func: Callable that takes a value and returns:
                  - True/None if valid
                  - False or error string if invalid
            error_message: Custom error message (used if func returns False).
        """
        super().__init__(error_message)
        self.func = func

    def validate(self, value: Any) -> str | None:
        """Run custom validation function."""
        try:
            result = self.func(value)
            if result is False:
                return self.error_message or "Validation failed"
            if isinstance(result, str):
                return result
            return None
        except Exception as e:
            return self.error_message or str(e)


class Field:
    """Represents a form field definition with type, validators, and metadata."""

    def __init__(
        self,
        field_type: type,
        required: bool = False,
        default: Any = None,
        validators: list[Validator] | None = None,
        error_message: str | None = None,
        coerce: bool = True,
    ):
        """Initialize a field definition.

        Args:
            field_type: The Python type to coerce to (str, int, float, bool).
            required: If True, field must be present and non-empty.
            default: Default value if field is missing or invalid.
            validators: List of Validator instances to apply.
            error_message: Custom error message for validation failures.
            coerce: Whether to attempt type coercion.
        """
        self.field_type = field_type
        self.required = required
        self.default = default
        self.validators = validators or []
        self.error_message = error_message
        self.coerce = coerce

    def coerce_value(self, raw_value: str | None) -> Any:
        """Coerce a raw string value to the field's type.

        Args:
            raw_value: Raw string value from form data, or None if missing.

        Returns:
            Coerced value of the appropriate type, or default if coercion fails.
        """
        if not self.coerce:
            return raw_value

        # Handle None/missing
        if raw_value is None:
            return self.default

        # String is always safe
        if self.field_type is str:
            stripped = raw_value.strip()
            return stripped if stripped != "" else (self.default if self.default is not None else "")

        # Type-specific coercion
        try:
            if self.field_type is int:
                if not raw_value:
                    return self.default if self.default is not None else 0
                if isinstance(raw_value, int):
                    return raw_value
                # After None/int checks and type hint, raw_value must be str
                stripped = raw_value.strip()
                if not stripped:
                    return self.default if self.default is not None else 0
                return int(stripped)
            elif self.field_type is float:
                if not raw_value:
                    return self.default if self.default is not None else 0.0
                if isinstance(raw_value, (int, float)):
                    return float(raw_value)
                # After None/int/float checks and type hint, raw_value must be str
                stripped = raw_value.strip()
                if not stripped:
                    return self.default if self.default is not None else 0.0
                return float(stripped)
            elif self.field_type is bool:
                return self._coerce_bool(raw_value)
        except (ValueError, TypeError):
            # Return default if set, otherwise type-specific default
            if self.default is not None:
                return self.default
            if self.field_type is int:
                return 0
            elif self.field_type is float:
                return 0.0
            elif self.field_type is bool:
                return False
            return self.default

        return raw_value

    def _coerce_bool(self, raw_value: str | None) -> bool:
        """Coerce a string value to boolean.

        Truthy values: "true", "1", "on", "yes", "y" (case-insensitive)
        Falsy values: "false", "0", "off", "no", "n", "" (case-insensitive)
        """
        if not raw_value:
            return self.default if self.default is not None else False

        stripped = raw_value.strip().lower()
        truthy_values = {"true", "1", "on", "yes", "y"}
        falsy_values = {"false", "0", "off", "no", "n", ""}

        if stripped in truthy_values:
            return True
        if stripped in falsy_values:
            return False

        # Default to False for unknown values if no default is specified
        return self.default if self.default is not None else False

    def validate(self, value: Any) -> list[str]:
        """Validate a coerced value against all validators.

        Args:
            value: The coerced value to validate.

        Returns:
            List of error messages. Empty list if validation passes.
        """
        errors: list[str] = []

        # Required check (only if value came from form data, not default)
        # Note: Required validation is handled at the schema level

        # Run all validators
        for validator in self.validators:
            error = validator.validate(value)
            if error:
                errors.append(error)

        return errors


def field(
    field_type: type,
    required: bool = False,
    default: Any = None,
    error_message: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    regex: str | None = None,
    validators: list[Validator] | None = None,
    coerce: bool = True,
):
    """Define a form field with validation rules.

    This is the primary way to define fields in a FormSchema subclass.

    Args:
        field_type: The Python type to coerce to (str, int, float, bool).
        required: If True, field must be present and non-empty.
        default: Default value if field is missing or invalid.
        error_message: Custom error message for validation failures.
            When multiple built-in validators are created (e.g., required + min_length),
            this same message is used for all of them. For different messages per
            constraint, use the `validators` parameter with explicit Validator instances.
        min_length: Minimum string length (for str fields).
        max_length: Maximum string length (for str fields).
        min_value: Minimum numeric value (for int/float fields).
        max_value: Maximum numeric value (for int/float fields).
        regex: Regex pattern that string must match.
        validators: List of custom Validator instances.
        coerce: Whether to attempt type coercion (default: True).

    Returns:
        Field: Configured field definition.

    Example:
        class MySchema(FormSchema):
            # Single error_message applies to all built-in validators
            username = field(str, required=True, min_length=3, error_message="Invalid username")

            # Different messages per constraint using validators list
            password = field(
                str,
                validators=[
                    RequiredValidator("Password is required"),
                    MinLengthValidator(8, "Password must be at least 8 characters"),
                ]
            )
            age = field(int, default=0, min_value=0, max_value=150)
            email = field(str, regex=r'^[\\w.-]+@[\\w.-]+\\.\\w+$')
    """
    built_validators: list[Validator] = []

    # Note: error_message is shared across all built-in validators created below.
    # If you need different messages per constraint, use validators=[...] instead
    # of the individual parameters (required, min_length, etc.).
    # Add built-in validators based on parameters
    if required:
        built_validators.append(RequiredValidator(error_message))
    if min_length is not None:
        built_validators.append(MinLengthValidator(min_length, error_message))
    if max_length is not None:
        built_validators.append(MaxLengthValidator(max_length, error_message))
    if min_value is not None:
        built_validators.append(MinValueValidator(min_value, error_message))
    if max_value is not None:
        built_validators.append(MaxValueValidator(max_value, error_message))
    if regex is not None:
        built_validators.append(RegexValidator(regex, error_message))

    # Combine with custom validators (custom validators run first)
    all_validators = (validators or []) + built_validators

    return Field(
        field_type=field_type,
        required=required,
        default=default,
        validators=all_validators,
        error_message=error_message,
        coerce=coerce,
    )


class FormSchemaMeta(type):
    """Metaclass to collect field definitions from schema classes."""

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> type:
        """Create a new schema class, collecting Field instances from class attributes.

        This metaclass removes Field instances from the class namespace and stores
        them in a separate _fields dictionary, so that instance attribute access
        works correctly. Also collects fields from parent classes to support inheritance.
        """
        # Collect field definitions from parent classes first (in reverse MRO order)
        fields: dict[str, Field] = {}

        # Process base classes in reverse MRO order
        # Using dict.update() ensures last-visited base wins conflicts
        for base in reversed(bases):
            base_fields: dict[str, Field] | None = getattr(base, "_fields", None)
            if base_fields is not None:
                fields.update(base_fields)

        # Create a clean namespace without Field instances
        clean_namespace: dict[str, Any] = {}

        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                # Child class fields override parent fields
                fields[attr_name] = attr_value
            else:
                clean_namespace[attr_name] = attr_value

        # Create the class with clean namespace
        cls = super().__new__(mcs, name, bases, clean_namespace)
        setattr(cls, "_fields", fields)
        return cls


class FormSchema(metaclass=FormSchemaMeta):
    """Base class for form validation schemas.

    Subclass this to define form schemas with typed, validated fields.

    Example:
        class UserForm(FormSchema):
            username = field(str, required=True, min_length=3)
            email = field(str, required=True, regex=r'@')
            age = field(int, default=18, min_value=0)

        # Usage in a trigger handler:
        @app.trigger_handler
        @validate_form(UserForm)
        async def create_user(form: UserForm) -> str:
            # form.username, form.email, form.age are validated and typed
            return f"Created user: {form.username}"
    """

    # Class attribute to store field definitions (populated by metaclass)
    _fields: dict[str, Field] = {}

    def __init__(self, data: dict[str, str] | None = None):
        """Initialize schema from form data.

        Args:
            data: Dictionary of form data (typically from request.form()).
                 Keys are field names, values are string values.
        """
        self._raw_data = data or {}
        self._errors: dict[str, list[str]] = {}
        self._values: dict[str, Any] = {}

        # Process each field definition
        for field_name, field_obj in self._fields.items():
            raw_value = self._raw_data.get(field_name, None)

            # Track if field is missing from input data
            is_missing = field_name not in self._raw_data

            # Handle missing values (field not in data at all)
            if is_missing:
                raw_value = None
                # fall through to coerce-then-validate below

            # Coerce value
            try:
                coerced_value = field_obj.coerce_value(raw_value)
            except Exception as e:
                self._errors[field_name] = [f"Invalid type: {e}"]
                self._values[field_name] = field_obj.default
                continue

            # For missing fields, only run RequiredValidator instances.
            # Content validators (length, range, pattern, custom) are meaningless
            # for a value that is absent, and custom validators may not handle None.
            if is_missing:
                errors = [
                    err
                    for v in field_obj.validators
                    if isinstance(v, RequiredValidator)
                    for err in [v.validate(None)]
                    if err
                ]
                if errors:
                    self._errors[field_name] = errors
                    self._values[field_name] = field_obj.default
                else:
                    # No validator requires the field, use coerced default
                    self._values[field_name] = coerced_value
            # Check required for empty values (after coercion)
            elif field_obj.required:
                if raw_value is None or not raw_value.strip():
                    self._errors[field_name] = [field_obj.error_message or "This field is required"]
                    self._values[field_name] = field_obj.default
                elif isinstance(coerced_value, str) and not coerced_value.strip():
                    self._errors[field_name] = [field_obj.error_message or "This field cannot be empty"]
                    self._values[field_name] = field_obj.default
                else:
                    # Validate coerced value
                    errors = field_obj.validate(coerced_value)
                    if errors:
                        self._errors[field_name] = errors
                    self._values[field_name] = coerced_value
            else:
                # For non-required fields, just validate and store
                errors = field_obj.validate(coerced_value)
                if errors:
                    self._errors[field_name] = errors
                self._values[field_name] = coerced_value

        # Run custom validate method if defined
        # This allows subclasses to add custom validation logic
        if hasattr(self, "validate") and callable(self.validate):
            # Get the method from the instance's class to avoid infinite recursion
            validate_method = self.__class__.validate
            if validate_method is not FormSchema.validate:
                # It's a custom validate method, call it
                try:
                    validate_method(self)
                except ValidationError as e:
                    # Merge errors from the ValidationError into self._errors
                    for field_name, field_errors in e.errors.items():
                        if field_name not in self._errors:
                            self._errors[field_name] = field_errors
                        else:
                            self._errors[field_name].extend(field_errors)

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to validated field values.

        This enables `form.username` syntax instead of `form._values['username']`.
        """
        if name in self._values:
            return self._values[name]
        # For IDE support, return default if field exists but has no value
        if name in self._fields:
            return self._values.get(name, self._fields[name].default)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __repr__(self) -> str:
        """Return string representation of the schema instance."""
        values_repr = ", ".join(f"{k}={v!r}" for k, v in self._values.items())
        return f"{self.__class__.__name__}({values_repr})"

    @property
    def errors(self) -> dict[str, list[str]]:
        """Get validation errors as a dictionary.

        Returns:
            Dictionary mapping field names to lists of error messages.
        """
        return self._errors.copy()

    @property
    def is_valid(self) -> bool:
        """Check if the schema passed validation.

        Returns:
            True if there are no validation errors, False otherwise.
        """
        return len(self._errors) == 0

    def validate(self) -> "FormSchema":
        """Run validation and raise ValidationError if invalid.

        Returns:
            self for method chaining.

        Raises:
            ValidationError: If validation fails.
        """
        if not self.is_valid:
            raise ValidationError(self.errors)
        return self


def _validate_and_call_sync(
    handler: Callable[..., Any],
    schema_class: type[FormSchema],
    handle_errors: bool,
    form_data_param: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """Synchronous internal helper to perform validation and call handler."""
    # Get the handler signature to find the expected parameter name
    sig = inspect.signature(handler)
    handler_params = list(sig.parameters.keys())

    # Try to find form_data in kwargs first, using the specified param name
    form_data: dict[str, str] | None = kwargs.pop(form_data_param, None)

    # Also try 'form_data' as a fallback since that's what the trigger route uses
    if form_data is None:
        form_data = kwargs.pop("form_data", None)

    # Try to find it in positional args based on handler signature
    if form_data is None:
        for i, param_name in enumerate(handler_params):
            if param_name == form_data_param or param_name == "form_data":
                if i < len(args):
                    form_data = args[i]
                    args = args[:i] + args[i + 1 :]
                break

    # If still no form_data, use empty dict
    if form_data is None:
        form_data = {}

    # Instantiate and validate schema
    schema = schema_class(form_data)

    if handle_errors and not schema.is_valid:
        raise ValidationError(schema.errors)

    # If handle_errors=False, inject errors dict
    if not handle_errors:
        kwargs["errors"] = schema.errors

    # Determine the parameter name to use for the schema instance
    # Try the specified form_data_param first, then look for common names
    target_param = form_data_param
    if target_param not in handler_params and len(handler_params) > 0:
        # Try to find a parameter that could be the form parameter
        for param in handler_params:
            if param in ("form", "form_data", form_data_param):
                target_param = param
                break
        else:
            # Use the first parameter if we can't find a match
            target_param = handler_params[0]

    # Inject the schema instance with the target parameter name
    kwargs[target_param] = schema

    # Call original handler
    try:
        return handler(*args, **kwargs)
    except TypeError as e:
        # Handle case where handler signature doesn't match
        # Try calling with just schema as the first argument
        try:
            return handler(schema)
        except Exception:
            # Re-raise original error
            raise e


async def _validate_and_call_async(
    handler: Callable[..., Awaitable[Any]],
    schema_class: type[FormSchema],
    handle_errors: bool,
    form_data_param: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """Asynchronous internal helper to perform validation and call handler."""
    # Get the handler signature to find the expected parameter name
    sig = inspect.signature(handler)
    handler_params = list(sig.parameters.keys())

    # Try to find form_data in kwargs first, using the specified param name
    form_data: dict[str, str] | None = kwargs.pop(form_data_param, None)

    # Also try 'form_data' as a fallback since that's what the trigger route uses
    if form_data is None:
        form_data = kwargs.pop("form_data", None)

    # Try to find it in positional args based on handler signature
    if form_data is None:
        for i, param_name in enumerate(handler_params):
            if param_name == form_data_param or param_name == "form_data":
                if i < len(args):
                    form_data = args[i]
                    args = args[:i] + args[i + 1 :]
                break

    # If still no form_data, use empty dict
    if form_data is None:
        form_data = {}

    # Instantiate and validate schema
    schema = schema_class(form_data)

    if handle_errors and not schema.is_valid:
        raise ValidationError(schema.errors)

    # If handle_errors=False, inject errors dict
    if not handle_errors:
        kwargs["errors"] = schema.errors

    # Determine the parameter name to use for the schema instance
    # Try the specified form_data_param first, then look for common names
    target_param = form_data_param
    if target_param not in handler_params and len(handler_params) > 0:
        # Try to find a parameter that could be the form parameter
        for param in handler_params:
            if param in ("form", "form_data", form_data_param):
                target_param = param
                break
        else:
            # Use the first parameter if we can't find a match
            target_param = handler_params[0]

    # Inject the schema instance with the target parameter name
    kwargs[target_param] = schema

    # Call original handler
    try:
        result = handler(*args, **kwargs)
        if inspect.iscoroutinefunction(handler):
            return await result
        return result
    except TypeError as e:
        # Handle case where handler signature doesn't match
        # Try calling with just schema as the first argument
        try:
            result = handler(schema)
            if inspect.iscoroutinefunction(handler):
                return await result
            return result
        except Exception:
            # Re-raise original error
            raise e


def validate_form(
    schema_class: type[FormSchema],
    handle_errors: bool = True,
    form_data_param: str = "form_data",
):
    """Decorator to validate form data against a schema.

    This decorator intercepts the form_data parameter from trigger handlers,
    validates it against the specified schema, and injects the validated
    schema instance as a parameter.

    Args:
        schema_class: The FormSchema subclass to use for validation.
        handle_errors: If True, raises ValidationError on validation failure.
                      If False, injects errors dict as additional parameter.
        form_data_param: Name of the parameter containing form data (default: "form_data").

    Usage:
        # With error handling (raises ValidationError on failure):
        @app.trigger_handler
        @validate_form(MySchema)
        async def handler(form: MySchema) -> str:
            # form is validated schema instance
            return f"Received: {form.title}"

        # Without error handling (errors passed to handler):
        @app.trigger_handler
        @validate_form(MySchema, handle_errors=False)
        async def handler(form: MySchema, errors: dict) -> str:
            if errors:
                return show_errors(errors)
            # Process valid form...

    Raises:
        ValidationError: If handle_errors=True and validation fails.
    """

    def decorator(handler: Callable[_P, _T]) -> Callable[..., _T]:
        # Get the original signature
        sig = inspect.signature(handler)

        # Create new parameters that include form_data if not already present
        # This ensures FastAPI's route_wrapper detects that we need form_data
        new_params: list[inspect.Parameter] = []
        for param in sig.parameters.values():
            new_params.append(param)

        # Add form_data parameter if not present
        if "form_data" not in sig.parameters:
            new_params.append(
                inspect.Parameter(
                    "form_data",
                    inspect.Parameter.KEYWORD_ONLY,
                    default=inspect.Parameter.empty,
                    annotation=dict[str, str],
                )
            )

        new_sig = sig.replace(parameters=new_params)

        # Create wrapper functions
        if inspect.iscoroutinefunction(handler):

            @functools.wraps(handler)
            async def async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
                return cast(_T, await _validate_and_call_async(
                    cast(Callable[..., Awaitable[Any]], handler),
                    schema_class, handle_errors, form_data_param, args, kwargs,
                ))

            wrapped: Callable[..., _T] = cast(Callable[..., _T], async_wrapper)
        else:

            @functools.wraps(handler)
            def sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
                return cast(_T, _validate_and_call_sync(
                    cast(Callable[..., Any], handler),
                    schema_class, handle_errors, form_data_param, args, kwargs,
                ))

            wrapped = cast(Callable[..., _T], sync_wrapper)

        # Set the new signature that includes form_data
        wrapped.__signature__ = new_sig  # type: ignore
        wrapped.__annotations__ = handler.__annotations__  # type: ignore

        return wrapped  # type: ignore

    return decorator
