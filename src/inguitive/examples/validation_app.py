"""
Form validation example using inguitive.

Run with: uvicorn inguitive.examples.validation_app:app --reload

Declarative Form Validation
---------------------------
This example demonstrates inguitive's validation layer: a ``FormSchema``
subclass declares typed, validated fields with ``field()``, and the
``@validate_form`` decorator intercepts the posted ``form_data`` before the
handler runs, coercing values to their declared types and running validators.

Two modes are worth knowing about (the parameter is named
``handle_errors``, but it really controls *raising*: ``True`` raises,
``False`` passes the errors dict to the handler):

- ``handle_errors=True`` (the default): invalid input raises
  ``ValidationError`` and the handler never runs. Use this when you only
  care about the happy path.
- ``handle_errors=False``: the handler still runs and receives an extra
  ``errors`` dict (``{field_name: [messages]}``) alongside the typed schema
  instance. Use this when you want to show per-field error messages in the
  UI, as this example does.

The schema here exercises the main built-in validators and a custom one:

| Field     | Type | Constraints                                         |
|-----------|------|-----------------------------------------------------|
| username  | str  | required, min_length=3, max_length=20              |
| email     | str  | required, regex (basic email pattern)               |
| age       | int  | min_value=0, max_value=150 (coerced from str)        |
| code      | str  | ``CustomValidator`` — must start with "ING-"        |

On submit, the handler stores either a success line or the per-field error
messages in ``result_state`` and the display panel re-renders via
auto-propagation. Contrast with ``form_app.py``, which receives raw
``form_data`` as an untyped ``dict[str, str]`` with no validation.

To test:
1. Submit empty — username, email, and code errors appear
2. Submit "ab" as username — min_length error appears
3. Submit a non-numeric age — coercion falls back, range errors may appear
4. Submit valid values — "Registered: <username>" appears
"""

from inguitive import (
    Button,
    CustomValidator,
    Div,
    Form,
    FormSchema,
    Input,
    Label,
    State,
    Text,
    create_app,
    field,
    validate_form,
)

# --- App Setup ---
app = create_app()


# --- State Instances ---
# Holds either a success message or a dict of per-field error lists.
result_state = State(None, "result_state")


# --- Schema ---
class RegistrationSchema(FormSchema):
    """Declarative schema for the registration form.

    Each ``field()`` declares a Python type (values are coerced from the
    posted strings), plus constraints expressed as built-in validator
    parameters or explicit ``Validator`` instances in the ``validators``
    list. The metaclass collects these into ``_fields`` so the handler sees
    typed attributes (``form.username`` is a str, ``form.age`` is an int).
    """

    username = field(str, required=True, min_length=3, max_length=20)
    email = field(str, required=True, regex=r"^[\w.-]+@[\w.-]+\.\w+$")
    age = field(int, default=0, min_value=0, max_value=150)
    code = field(
        str,
        required=True,
        validators=[
            CustomValidator(
                lambda v: v.startswith("ING-") if isinstance(v, str) else False,
                error_message="Code must start with 'ING-'",
            )
        ],
    )


# --- Trigger Handlers ---
@app.trigger_handler
@validate_form(RegistrationSchema, handle_errors=False)
def register(form: RegistrationSchema, errors: dict) -> None:
    """Validate and store the result of the registration attempt.

    With ``handle_errors=False``, this runs whether or not the form is
    valid. ``errors`` is ``{field_name: [messages]}`` (empty when valid) and
    ``form`` holds the coerced values. We store either the success line or
    the error dict in ``result_state`` and let auto-propagation re-render
    the panel.
    """
    if errors:
        result_state.set({"errors": errors})
    else:
        result_state.set({"success": f"Registered: {form.username} (age {form.age})"})


# --- Components ---
def Field(label: str, control, hint: str = "") -> Div:  # noqa: N802
    """A labelled field with an optional hint below."""
    return Div(
        Label(label, css="font-medium text-slate-700"),
        control,
        Text(hint, css="text-xs text-slate-500") if hint else None,
        css="space-y-1",
    )


def ResultPanel() -> Div:  # noqa: N802
    """Show either the per-field error list or the success line."""

    def display_text() -> str:
        result = result_state.get()
        if result is None:
            return ""
        if "success" in result:
            return result["success"]
        # errors dict: {field: [messages]} — flatten into one line per message
        lines = []
        for field_name, messages in result.get("errors", {}).items():
            for message in messages:
                lines.append(f"{field_name}: {message}")
        return "Fix these:\n" + "\n".join(lines)

    return Div(
        Text(
            display_text,
            id="result-panel",
            css="whitespace-pre-line text-slate-900",
            listen_to="result_state",
        ),
        css="max-w-md mx-auto mt-6 p-4 bg-slate-100 rounded-lg",
    )


def ValidationForm() -> Div:  # noqa: N802
    """The registration form with one input per schema field."""
    return Div(
        Form(
            Field("Username", Input(id="username", placeholder="3-20 characters"), "Required, 3-20 chars"),
            Field("Email", Input(id="email", type="email", placeholder="you@example.com"), "Required, must be a valid email"),
            Field("Age", Input(id="age", type="number", placeholder="0-150"), "Coerced to int, 0-150"),
            Field("Code", Input(id="code", placeholder="ING-XXXX"), "Must start with ING-"),
            Button(
                "Register",
                type="submit",
                css="w-full bg-slate-600 text-white rounded-md p-2 font-semibold cursor-pointer",
            ),
            trigger="register",
            css="space-y-4 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md",
        ),
        ResultPanel(),
        css="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50",
    )


# --- Routes ---
@app.page("/")
def home():
    return ValidationForm()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.validation_app:app", host="0.0.0.0", port=8000, reload=True)
