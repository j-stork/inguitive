"""
Form components example using inguitive.

Run with: uvicorn inguitive.examples.form_app:app --reload

Form Components and form_data
-----------------------------
This example demonstrates inguitive's form components and how a trigger
handler receives submitted values.

Every form input component maps to an HTML element and auto-sets its ``name``
attribute to its ``id`` when no explicit ``name`` is given, so the key in
``form_data`` matches the ``id``. The handler declares a ``form_data``
parameter and inguitive auto-injects the submitted fields as a
``dict[str, str]``; query parameters from ``trigger_args`` are merged in too.

Components shown here, one of each:

| Component  | HTML element        | Notable parameter |
|------------|---------------------|--------------------|
| ``Input``  | ``<input>``         | ``type``, ``placeholder`` |
| ``Textarea`` | ``<textarea>``    | ``rows`` |
| ``Select`` | ``<select>``        | ``options=[(value, label), ...]`` |
| ``Checkbox`` | ``<input type=checkbox>`` | ``checked`` |
| ``Radio``  | ``<input type=radio>`` | radios share one ``name`` for a group |
| ``Label``  | ``<label>``         | ``for_`` (trailing underscore avoids the Python keyword) |
| ``Form``   | ``<form>``          | ``trigger=`` wires HTMX submission |

On submit, the handler merges the posted fields into ``form_state`` and the
``form_display`` panel re-renders via auto-propagation (no explicit return —
see ``auto_propagation_app.py``). Note checkboxes only post when checked, so
an absent key means unchecked; the handler normalises that to a boolean.

Contrast with ``trigger_args_app.py`` (data baked into the component at render
time, no form) and ``validation_app.py`` (typed, validated form data via
``FormSchema`` instead of a raw ``dict``).

To test:
1. Fill in the fields, pick a country, tick the box, choose a gender, submit
2. The "You submitted" panel updates with the values you entered
3. Submit again with different values — the panel reflects the new submission
"""

from inguitive import (
    Button,
    Checkbox,
    Div,
    Form,
    Input,
    Label,
    Radio,
    Select,
    State,
    Text,
    Textarea,
    create_app,
)

# --- App Setup ---
app = create_app()


# --- State Instances ---
# Holds the last submitted form data as a dict. Display reads from this.
form_state = State({}, "form_state")


# --- Trigger Handlers ---
@app.trigger_handler
def submit(form_data: dict):
    """Store the submitted form data for display.

    ``form_data`` is auto-injected: inguitive sees the ``form_data`` parameter
    name and passes the posted fields as a ``dict[str, str]``. Checkboxes only
    submit a value when checked, so an absent ``terms`` key means unchecked —
    normalise it to a bool here so the display can render it cleanly.
    """
    data = dict(form_data)
    data["terms"] = data.get("terms") == "on"
    form_state.set(data)
    # No return: auto-propagation re-renders form_display (see app docstring).


# --- Components ---
def Field(label: str, control) -> Div:  # noqa: N802
    """A labelled form field: label on top, control below."""
    return Div(
        Label(label, css="font-medium text-slate-700"),
        control,
        css="space-y-1",
    )


def GenderOption(value: str, label: str) -> Div:  # noqa: N802
    """A radio option with its label, for the shared ``gender`` group."""
    radio_id = f"gender-{value}"
    return Div(
        Radio(id=radio_id, name="gender", value=value),
        Label(label, for_=radio_id),
        css="flex items-center gap-2",
    )


def RegistrationForm() -> Div:  # noqa: N802
    """One form containing one of every form component."""
    return Div(
        Form(
            Field("Name", Input(id="name", placeholder="Enter your name")),
            Field("Email", Input(id="email", type="email", placeholder="you@example.com")),
            Field("Bio", Textarea(id="bio", placeholder="Tell us about yourself", rows=3)),
            Field(
                "Country",
                Select(
                    id="country",
                    options=[("de", "Germany"), ("fr", "France"), ("us", "United States")],
                ),
            ),
            Div(
                Checkbox(id="terms"),
                Label("I agree to the terms", for_="terms"),
                css="flex items-center gap-2",
            ),
            Div(
                Text("Gender", css="font-medium text-slate-700"),
                Div(
                    GenderOption("male", "Male"),
                    GenderOption("female", "Female"),
                    GenderOption("other", "Other"),
                    css="flex gap-6",
                ),
                css="space-y-1",
            ),
            Button("Submit", type="submit", css="w-full bg-slate-600 text-white rounded-md p-2 font-semibold cursor-pointer"),
            trigger="submit",
            css="space-y-4 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md",
        ),
        Div(
            Text(
                lambda: _render_summary(form_state.get()),
                id="form_display",
                css="text-slate-900 whitespace-pre-line",
                listen_to="form_state",
            ),
            css="max-w-md mx-auto mt-6 p-4 bg-slate-100 rounded-lg",
        ),
        css="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50",
    )


def _render_summary(data: dict) -> str:
    """Render the submitted data as a readable summary block."""
    if not data:
        return "You submitted: (nothing yet)"
    lines = [
        f"Name: {data.get('name', '')}",
        f"Email: {data.get('email', '')}",
        f"Bio: {data.get('bio', '')}",
        f"Country: {data.get('country', '')}",
        f"Terms accepted: {'Yes' if data.get('terms') else 'No'}",
        f"Gender: {data.get('gender', '')}",
    ]
    return "You submitted:\n" + "\n".join(lines)


# --- Routes ---
@app.page("/")
def home():
    return RegistrationForm()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.form_app:app", host="0.0.0.0", port=8000, reload=True)
