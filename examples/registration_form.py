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
                id="name",
                name="name",
                placeholder="Enter your name",
                value=name_state.get,
                listen_to="name_state",
                hx_post="/update_name",
                hx_target="#hx-target",
                hx_trigger="keyup changed delay:500ms",
                cls="w-full p-2 border rounded-md mb-4"
            ),
            Input(
                id="email",
                name="email",
                type="email",
                placeholder="Enter your email",
                value=email_state.get,
                listen_to="email_state",
                hx_post="/update_email",
                hx_target="#hx-target",
                hx_trigger="keyup changed delay:500ms",
                cls="w-full p-2 border rounded-md mb-4"
            ),
            Input(
                id="password",
                name="password",
                type="password",
                placeholder="Enter your password",
                value=password_state.get,
                listen_to="password_state",
                hx_post="/update_password",
                hx_target="#hx-target",
                hx_trigger="keyup changed delay:500ms",
                cls="w-full p-2 border rounded-md mb-4"
            ),
            Button(
                "Register",
                type="submit",
                on_click="register",
                cls="w-full bg-blue-500 text-white p-2 rounded-md hover:bg-blue-600"
            ),
            action="/register",
            method="POST",
            id="registration-form",
            cls="space-y-4 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md"
        ),
        # Confirmation display
        Div(
            Label(
                text=lambda: f"Welcome, {name_state.get()}!" if name_state.get() else "Fill out the form",
                id="welcome",
                cls="text-xl font-bold text-center mt-6"
            ),
            Label(
                text=lambda: f"Email: {email_state.get()}" if email_state.get() else "",
                id="email-display",
                cls="text-center mt-2"
            ),
            id="confirmation",
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


@app.post("/update_name", response_class=HTMLResponse)
async def update_name(request: Request) -> str:
    """Update name state from form input."""
    form_data = await request.form()
    name_state.set(form_data.get("name", ""))
    return ""


@app.post("/update_email", response_class=HTMLResponse)
async def update_email(request: Request) -> str:
    """Update email state from form input."""
    form_data = await request.form()
    email_state.set(form_data.get("email", ""))
    return ""


@app.post("/update_password", response_class=HTMLResponse)
async def update_password(request: Request) -> str:
    """Update password state from form input."""
    form_data = await request.form()
    password_state.set(form_data.get("password", ""))
    return ""


@app.post("/register", response_class=HTMLResponse)
def register() -> str:
    """Handle form submission."""
    # Form submission handled by OOB swaps from the field updates
    # Just return empty - the confirmation display reacts to state changes
    return ""


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("examples.registration_form:app", host="0.0.0.0", port=8000, reload=True)
