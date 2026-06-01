"""
Registration form example using INGUITIVE framework.

Demonstrates form components (Form, Input, Button, Label) with reactive state.

Run with: uvicorn examples.registration_form:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from inguitive import Form, Input, Textarea, Select, Checkbox, Radio, Button, Label, Text, Div, State
from inguitive.htmx import update_components

# --- State Instances ---
name_state = State("", "name_state")
email_state = State("", "email_state")
password_state = State("", "password_state")
bio_state = State("", "bio_state")
country_state = State("us", "country_state")
terms_state = State(False, "terms_state")
gender_state = State("male", "gender_state")


# --- App Setup ---
app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


# --- Helper Functions ---
def GenderRadio(id: str, value: str, label: str) -> Div:
    return Div(
        Radio(id=id, name="gender", value=value),
        Label(label, for_=id),
        cls="flex items-baseline gap-2"
    )


# --- Registration Form Component ---
def RegistrationForm() -> Div:
    """Registration form with reactive state updates."""
    return Div(
        # Form
        Form(
            Input(
                id="name",
                placeholder="Enter your name",
                cls="w-full p-2 border border-zinc-500 rounded-md",
            ),
            Input(
                id="email",
                type="email",
                placeholder="Enter your email",
                cls="w-full p-2 border border-zinc-500 rounded-md"
            ),
            Input(
                id="password",
                type="password",
                placeholder="Enter your password",
                cls="w-full p-2 border border-zinc-500 rounded-md"
            ),
            Textarea(
                id="bio",
                placeholder="Tell us about yourself",
                rows=3,
                cls="w-full p-2 border border-zinc-500 rounded-md"
            ),
            Select(
                id="country",
                options=[("us", "United States"), ("de", "Germany"), ("fr", "France")],
                cls="w-full p-2 border border-zinc-500 rounded-md"
            ),
            Div(
                Checkbox(id="terms", name="terms"),
                Label("I agree to the terms and conditions", for_="terms"),
                cls="flex items-baseline gap-2"
            ),
            Div(
                GenderRadio(id="gender-male", value="male", label="Male"),
                GenderRadio(id="gender-female", value="female", label="Female"),
                GenderRadio(id="gender-other", value="other", label="Other"),
                cls="flex items-baseline gap-6"
            ),
            Button(
                "Register",
                type="submit",
                on_click="register",
                cls="w-full bg-blue-500 text-white font-bold p-2 rounded-md hover:bg-blue-600"
            ),
            cls="space-y-6 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md"
        ),
        # Confirmation display
        Div(
            Text(
                lambda: f"Name: {name_state.get()}" if name_state.get() else "Name:",
                listen_to="name_state",
                cls="text-center"
            ),
            Text(
                lambda: f"Email: {email_state.get()}" if email_state.get() else "Email:",
                listen_to="email_state",
                cls="text-center"
            ),
            Text(
                lambda: f"Password: {'*' * len(password_state.get())}" if password_state.get() else "Password:",
                listen_to="password_state",
                cls="text-center"
            ),
            Text(
                lambda: f"Bio: {bio_state.get()}" if bio_state.get() else "Bio:",
                listen_to="bio_state",
                cls="text-center"
            ),
            Text(
                lambda: f"Country: {country_state.get()}" if country_state.get() else "Country:",
                listen_to="country_state",
                cls="text-center"
            ),
            Text(
                lambda: f"Terms accepted: {'Yes' if terms_state.get() is not False else 'No'}",
                listen_to="terms_state",
                cls="text-center"
            ),
            Text(
                lambda: f"Gender: {gender_state.get()}" if gender_state.get() else "Gender:",
                listen_to="gender_state",
                cls="text-center"
            ),
            cls="text-xl font-bold mt-6 space-y-3"
        ),
        cls="w-full min-h-screen flex flex-col items-center justify-center p-6"
    )


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    # TODO: Could this be made more elegant for example by creating a dedicated render function?
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "content": RegistrationForm().render()}
    )


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request) -> str:
    """Handle form submission."""
    listeners = set()
    form_data = await request.form()
    if form_data:
        # Map all form fields to their states
        field_states = [
            ("name", name_state),
            ("email", email_state),
            ("password", password_state),
            ("bio", bio_state),
            ("country", country_state),
            ("terms", terms_state),
            ("gender", gender_state),
        ]
        for field, state in field_states:
            field_value = form_data.get(field, "")
            # For checkbox, handle boolean value
            if field == "terms":
                field_value = field_value == "on"  # Checkboxes send "on" when checked
            if field_value != state.get():
                state.set(field_value)
                listeners.update(state.listeners)
    if listeners:
        return update_components(*listeners)
    return ""
            

# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("examples.registration_form:app", host="0.0.0.0", port=8000, reload=True)
