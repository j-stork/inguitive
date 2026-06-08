"""
Counter example application using INGUITIVE framework.

Run with: uvicorn examples.counter_app:app --reload

Per-Session Isolation Demonstration
-----------------------------------
This example demonstrates INGUITIVE's per-session state isolation.
Each browser tab maintains its own independent counter and theme state.

To test:
1. Open this app in two separate browser tabs
2. Note the unique Session ID displayed below the counter in each tab
3. Increment the counter in Tab 1 - Tab 2's counter remains unchanged
4. Toggle theme in Tab 1 - Tab 2's theme remains unchanged

This proves that State values are fully isolated per user session.
"""

from pathlib import Path

from inguitive import State, Div, Button, Label, Icon, create_app, get_session_id, trigger_handler, page
from inguitive.css import BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS
from inguitive.htmx import update_components
from inguitive.svg import MOON, SUN

# --- State Instances ---
counter_state = State(0, "counter_state")
theme_state = State("light", "theme_state")

# --- Trigger Handlers ---
@trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)

@trigger_handler
def reset():
    counter_state.set(0)
    return update_components(*counter_state.listeners)

@trigger_handler
def toggle_theme():
    """Toggle between light and dark theme."""
    current: str = theme_state.get()
    new_theme: str = "dark" if current == "light" else "light"
    theme_state.set(new_theme)
    return update_components(*theme_state.listeners)

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
                    Icon(lambda: MOON if theme_state.get() == "light" else SUN, css="w-6 h-6"),
                    trigger="toggle_theme",
                    id="theme-toggle",
                    css=f"{BUTTON_SECONDARY_CSS}"
                ),
                css="w-full flex justify-end",
            ),
            Label(
                text=lambda: f"Count: {counter_state.get()}",
                id="counter-label",
                css=get_counter_style,
                listen_to="counter_state"
            ),
            Div(
                f"Session: {get_session_id()}",
                css="text-xs text-gray-500 text-center mt-2"
            ),
            Button("+1", trigger="increment", css=f"{BUTTON_PRIMARY_CSS} w-full"),
            Button("Reset", trigger="reset", css=f"{BUTTON_SECONDARY_CSS} w-full"),
            id="counter-card",
            css="overflow-hidden rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm",
        ),
        id="theme-container",
        css=lambda: f"w-full min-h-screen {get_theme_bg()} flex items-center justify-center",
        listen_to="theme_state"
    )


# --- Routes ---
@page("/")
def home():
    return Counter()


# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent / "templates")


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("examples.counter_app:app", host="0.0.0.0", port=8000, reload=True)
