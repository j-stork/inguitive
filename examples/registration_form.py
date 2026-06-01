"""
Registration form example using INGUITIVE framework.

Demonstrates form components (Form, Input, Button, Label) with reactive state.

Run with: uvicorn examples.registration_form:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from inguitive import Form, Input, Button, Label, Div, State
from inguitive.htmx import update_components

# --- State Instances ---
name_state = State("", "name_state")
email_state = State("", "email_state")
password_state = State("", "password_state")


# --- App Setup ---
app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


# --- Registration Form Component ---
def RegistrationForm() -> Div:
    """Registration form with reactive state updates."""
    return Div(
        # Form
        Form(
            Input(
                name="name",
                placeholder="Enter your name",
                value=name_state.get,
                cls="w-full p-2 border rounded-md mb-4"
            ),
            Input(
                name="email",
                type="email",
                placeholder="Enter your email",
                value=email_state.get,
                cls="w-full p-2 border rounded-md mb-4"
            ),
            Input(
                name="password",
                type="password",
                placeholder="Enter your password",
                value=password_state.get,
                cls="w-full p-2 border rounded-md mb-4"
            ),
            Button(
                "Register",
                type="submit",
                on_click="register",
                cls="w-full bg-blue-500 text-white p-2 rounded-md hover:bg-blue-600"
            ),
            cls="space-y-4 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md"
        ),
        # Confirmation display
        Div(
            Label(
                text=lambda: f"Name: {name_state.get()}" if name_state.get() else "Name:",
                listen_to="name_state",
                cls="text-xl font-bold text-center mt-6"
            ),
            Label(
                text=lambda: f"Email: {email_state.get()}" if email_state.get() else "Email:",
                listen_to="email_state",
                cls="text-center mt-2"
            ),
            Label(
                text=lambda: f"Password: {password_state.get()}" if password_state.get() else "Password:",
                listen_to="password_state",
                cls="text-center mt-2"
            ),
            cls="mt-6"
        ),
        cls="w-full min-h-screen flex flex-col items-center justify-center p-4"
    )


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
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
        for field, state in [("name", name_state), ("email", email_state), ("password", password_state)]:
            field_value = form_data.get(field, "")
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
