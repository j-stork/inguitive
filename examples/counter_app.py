"""
Counter example application using INGUITIVE framework.

Run with: uvicorn examples.counter_app:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from inguitive import State, Div, Button, Label, Icon
from inguitive.css import BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS
from inguitive.htmx import update_components
from inguitive.svg import MOON, SUN

# --- State Instances ---
counter_state = State(0, "counter_state")
theme_state = State("light", "theme_state")

# --- App Setup ---
app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


# --- Dynamic styling functions ---
def get_counter_style() -> str:
    """Dynamic styling based on counter value."""
    count = counter_state.get()
    base = "text-xl text-center"
    if count > 5:
        return f"{base} text-red-500 font-bold"
    elif count < 0:
        return f"{base} text-blue-500"
    return base


def get_theme_bg() -> str:
    """Dynamic background based on theme state."""
    return "bg-slate-100" if theme_state.get() == "light" else "bg-slate-800"


# --- Counter Component ---
def Counter() -> Div:
    """Main counter component demonstrating INGUITIVE features."""
    return Div(
        Div(
            Div(
                Button(
                    Icon(lambda: MOON if theme_state.get() == "light" else SUN, cls="w-6 h-6"),
                    on_click="toggle_theme",
                    id="theme-toggle",
                    cls=f"{BUTTON_SECONDARY_CSS}"
                ),
                cls="w-full flex justify-end",
            ),
            Label(
                text=lambda: f"Count: {counter_state.get()}",
                id="counter-label",
                cls=get_counter_style,
                listen_to="counter_state"
            ),
            Button("+1", on_click="increment", cls=f"{BUTTON_PRIMARY_CSS} w-full"),
            Button("Reset", on_click="reset", cls=f"{BUTTON_SECONDARY_CSS} w-full"),
            id="counter-card",
            cls="overflow-hidden rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm"
        ),
        id="theme-container",
        cls=lambda: f"w-full min-h-screen {get_theme_bg()} flex items-center justify-center",
        listen_to="theme_state"
    )


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "content": Counter().render()}
    )


@app.post("/increment", response_class=HTMLResponse)
def increment() -> str:
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)


@app.post("/reset", response_class=HTMLResponse)
def reset() -> str:
    counter_state.set(0)
    return update_components(*counter_state.listeners)


@app.post("/toggle_theme", response_class=HTMLResponse)
def toggle_theme() -> str:
    """Toggle between light and dark theme."""
    current: str = theme_state.get()
    new_theme: str = "dark" if current == "light" else "light"
    theme_state.set(new_theme)
    return update_components(*theme_state.listeners)


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("examples.counter_app:app", host="0.0.0.0", port=8000, reload=True)
