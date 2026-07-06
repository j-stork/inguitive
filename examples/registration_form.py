"""
Registration form example using INGUITIVE framework.

Demonstrates form components (Form, Input, Button, Label) with reactive state.

Run with: uvicorn examples.registration_form:app --reload
"""

from pathlib import Path

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
    update_components,
    dynamic,
)

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent.parent / "templates")

# --- State Instances ---
# Use collective State for form data (simpler pattern)
form_state = State({}, "form_state")


# --- Trigger Handlers ---
@app.trigger_handler
async def register(form_data: dict) -> str:
    """Handle form submission with auto-injected form_data."""
    current = form_state.get()
    new_data = {**current, **form_data}

    # Handle checkboxes: "on" -> True
    if "terms" in new_data:
        new_data["terms"] = new_data["terms"] == "on"

    form_state.set(new_data)
    return update_components("form_display")


# --- Helper Functions ---
def GenderRadio(id: str, value: str, label: str) -> Div:  # noqa: N802
    return Div(Radio(id=id, name="gender", value=value), Label(label, for_=id), css="flex items-baseline gap-2")


# --- Registration Form Component ---
def RegistrationForm() -> Div:  # noqa: N802
    """Registration form with reactive state updates."""
    return Div(
        # Form
        Form(
            Input(
                id="name",
                placeholder="Enter your name",
                css="w-full p-2 border border-zinc-500 rounded-md",
            ),
            Input(
                id="email",
                type="email",
                placeholder="Enter your email",
                css="w-full p-2 border border-zinc-500 rounded-md",
            ),
            Input(
                id="password",
                type="password",
                placeholder="Enter your password",
                css="w-full p-2 border border-zinc-500 rounded-md",
            ),
            Textarea(
                id="bio",
                placeholder="Tell us about yourself",
                rows=3,
                css="w-full p-2 border border-zinc-500 rounded-md",
            ),
            Select(
                id="country",
                options=[("us", "United States"), ("de", "Germany"), ("fr", "France")],
                css="w-full p-2 border border-zinc-500 rounded-md",
            ),
            Div(
                Checkbox(id="terms", name="terms"),
                Label("I agree to the terms and conditions", for_="terms"),
                css="flex items-baseline gap-2",
            ),
            Div(
                GenderRadio(id="gender-male", value="male", label="Male"),
                GenderRadio(id="gender-female", value="female", label="Female"),
                GenderRadio(id="gender-other", value="other", label="Other"),
                css="flex items-baseline gap-6",
            ),
            Button(
                "Register",
                type="submit",
                trigger="register",
                css="w-full bg-blue-500 text-white font-bold p-2 rounded-md hover:bg-blue-600",
            ),
            css="space-y-6 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md",
        ),
        # Confirmation display
        Div(
            Text(
                dynamic(f"Name: {form_state.get().get('name', '')}" if form_state.get().get("name") else "Name:"),
                css="text-center",
            ),
            Text(
                dynamic(f"Email: {form_state.get().get('email', '')}" if form_state.get().get("email") else "Email:"),
                css="text-center",
            ),
            Text(
                dynamic(f"Password: {'*' * len(form_state.get().get('password', ''))}" if form_state.get().get("password") else "Password:"),
                css="text-center",
            ),
            Text(
                dynamic(f"Bio: {form_state.get().get('bio', '')}" if form_state.get().get("bio") else "Bio:"),
                css="text-center",
            ),
            Text(
                dynamic(f"Country: {form_state.get().get('country', '')}" if form_state.get().get("country") else "Country:"),
                css="text-center",
            ),
            Text(dynamic(f"Terms accepted: {'Yes' if form_state.get().get('terms') else 'No'}"), css="text-center"),
            Text(
                dynamic(f"Gender: {form_state.get().get('gender', '')}" if form_state.get().get("gender") else "Gender:"),
                css="text-center",
            ),
            id="form_display",
            css="text-xl font-bold mt-6 space-y-3",
        ),
        css="w-full min-h-screen flex flex-col items-center justify-center p-6",
    )


# --- Routes ---
@app.page("/")
def home():
    return RegistrationForm()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.registration_form:app", host="0.0.0.0", port=8000, reload=True)
