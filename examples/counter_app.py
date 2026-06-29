"""
Counter example application using INGUITIVE framework.

Run with: uvicorn examples.counter_app:app --reload

Per-Session Isolation Demonstration
-----------------------------------
This example demonstrates INGUITIVE's per-session state isolation.
Each browser session maintains its own independent counter and theme state.

To test:
1. Open this app in one regular browser window and one incognito/private window
2. Note the unique Session ID displayed below the counter in each window
3. Increment the counter in Window 1 - Window 2's counter remains unchanged
4. Toggle theme in Window 1 - Window 2's theme remains unchanged

This proves that State values are fully isolated per user session.
"""

from pathlib import Path

from inguitive import Button, Div, Icon, Label, State, Text, create_app, get_session_id, update_components
from inguitive.svg import MOON, SUN

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent / "templates")

# --- State Instances ---
counter_state = State(0, "counter_state")
theme_state = State("light", "theme_state")


# --- CSS ---
COLOR_BASE = "slate"
COLOR_100 = f"{COLOR_BASE}-100"
COLOR_300 = f"{COLOR_BASE}-300"
COLOR_400 = f"{COLOR_BASE}-400"
COLOR_700 = f"{COLOR_BASE}-700"
COLOR_900 = f"{COLOR_BASE}-900"
COLOR_BRAND_1 = "blue-700"
COLOR_BRAND_2 = "fuchsia-600"
BUTTON_SHAPE = "p-3 rounded-md font-semibold cursor-pointer shadow-lg active:shadow-none"
BUTTON_PRIMARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_BRAND_1} to-{COLOR_BRAND_2} text-{COLOR_100}"
BUTTON_SECONDARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_400} to-{COLOR_300} text-{COLOR_900}"

# --- Trigger Handlers ---
@app.trigger_handler
def increment():
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)


@app.trigger_handler
def reset():
    counter_state.set(0)
    return update_components(*counter_state.listeners)


@app.trigger_handler
def toggle_theme():
    print("toggle_theme was triggered.")
    """Toggle between light and dark theme."""
    current: str = theme_state.get()
    new_theme: str = "dark" if current == "light" else "light"
    theme_state.set(new_theme)
    print(f"*theme_state.listeners = {theme_state.listeners}")
    return update_components(*theme_state.listeners)


# --- Dynamic styling functions ---
def get_counter_style() -> str:
    """Dynamic styling based on counter value."""
    count = counter_state.get()
    base = "text-xl text-center"
    if count > 5:
        return f"{base} text-red-500 font-bold"
    return f"{base} text-{COLOR_900}"


def get_theme_bg() -> str:
    """Dynamic background based on theme state."""
    return f"bg-{COLOR_100}" if theme_state.get() == "light" else f"bg-{COLOR_900}"


# --- Counter Component ---
def Counter() -> Div:
    """Main counter component demonstrating INGUITIVE features."""
    print(f"w-full min-h-screen {get_theme_bg()} flex items-center justify-center")
    return Div(
        Div(
            Div(
                Button(
                    Icon(lambda: MOON if theme_state.get() == "light" else SUN, css="w-6 h-6"),
                    trigger="toggle_theme",
                    id="theme-toggle",
                    css=BUTTON_PRIMARY,
                ),
                css="w-full flex justify-end",
            ),
            Text(
                text=lambda: f"Count: {counter_state.get()}",
                id="counter-label",
                css=lambda: get_counter_style(),
                listen_to="counter_state",
            ),
            Button("+1", trigger="increment", css=f"{BUTTON_PRIMARY} w-full"),
            Button("Reset", trigger="reset", css=f"{BUTTON_SECONDARY} w-full"),
            Text(f"Session: {get_session_id()}", css="text-xs text-gray-500 text-center"),
            id="counter-card",
            css="overflow-hidden rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm",
        ),
        id="theme-container",
        css=lambda: f"w-full min-h-screen {get_theme_bg()} flex items-center justify-center",
        listen_to="theme_state",
    )


# --- Routes ---
@app.page("/")
def home():
    return Counter()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.counter_app:app", host="0.0.0.0", port=8000, reload=True)
