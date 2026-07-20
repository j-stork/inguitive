"""
Counter example application using inguitive framework.

Run with: uvicorn examples.counter_app:app --reload

Per-Session Isolation Demonstration
-----------------------------------
This example demonstrates inguitive's per-session state isolation.
Each browser session maintains its own independent counter and theme state.

To test:
1. Open this app in one regular browser window and one incognito/private window
2. Note the unique Session ID displayed in each window
3. Increment the counter in Window 1 - Window 2's counter remains unchanged
4. Toggle theme in Window 1 - Window 2's theme remains unchanged

This proves that State values are fully isolated per user session.
"""

from pathlib import Path

from inguitive import Button, Div, Icon, State, Text, create_app, get_session_id, update_components
from inguitive.svg import MOON, SUN

# --- App Setup ---
app = create_app(template_dir=Path(__file__).parent.parent / "templates")


# --- State Instances ---
counter_state = State(0, "counter_state")
theme_state = State("light", "theme_state")


# --- CSS ---
COLOR_BASE = "slate"
COLOR_100 = f"{COLOR_BASE}-100"
COLOR_300 = f"{COLOR_BASE}-300"
COLOR_400 = f"{COLOR_BASE}-400"
COLOR_600 = f"{COLOR_BASE}-600"
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
    """Toggle between light and dark theme."""
    current: str = theme_state.get()
    new_theme: str = "dark" if current == "light" else "light"
    theme_state.set(new_theme)
    return update_components(*theme_state.listeners)


# --- Counter Component ---
def Counter() -> Div:  # noqa: N802
    """Main counter component demonstrating inguitive features."""

    def dynamic_icon() -> str:
        """Dynamic icon based on theme state."""
        return MOON if theme_state.get() == "light" else SUN

    def dynamic_text() -> str:
        """Dynamic text based on counter state."""
        return f"Count: {counter_state.get()}"

    def dynamic_text_css() -> str:
        """Dynamic styling based on counter value."""
        count = counter_state.get()
        base = "text-xl text-center"
        if count > 5:
            return f"{base} text-red-500 font-bold"
        return f"{base} text-{COLOR_900}"

    def dynamic_div_css() -> str:
        """Dynamic styling based on theme state."""
        bg = f"bg-{COLOR_100}" if theme_state.get() == "light" else f"bg-{COLOR_900}"
        return f"{bg} w-full min-h-screen flex items-center justify-center"

    return Div(
        Div(
            Div(
                Button(
                    Icon(
                        dynamic_icon,
                        css="w-6 h-6",
                    ),
                    trigger="toggle_theme",
                    id="theme-toggle",
                    css=BUTTON_PRIMARY,
                ),
                css="w-full flex justify-end",
            ),
            Text(
                text=dynamic_text,
                id="counter-label",
                css=dynamic_text_css,
                listen_to="counter_state",
            ),
            Button(
                "+1",
                trigger="increment",
                css=f"{BUTTON_PRIMARY} w-full",
            ),
            Button(
                "Reset",
                trigger="reset",
                css=f"{BUTTON_SECONDARY} w-full",
            ),
            Text(
                f"Session: {get_session_id()}",
                css=f"text-sm text-center text-{COLOR_600}",
            ),
            id="counter-card",
            css="overflow-hidden rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm",
        ),
        id="theme-container",
        css=dynamic_div_css,
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
