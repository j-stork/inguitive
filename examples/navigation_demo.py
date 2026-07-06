"""
Navigation Demo example using INGUITIVE framework.

Demonstrates two approaches to navigation:
1. Traditional multi-page navigation (URL changes)
2. SPA-style content switching (URL stays constant, content changes)

Run with: uvicorn examples.navigation_demo:app --reload
"""

from pathlib import Path

from inguitive import Button, Div, Link, State, Text, create_app, redirect, update_components, dynamic

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent.parent / "templates")


# --- CSS ---
COLOR_BASE = "slate"
COLOR_100 = f"{COLOR_BASE}-100"
COLOR_200 = f"{COLOR_BASE}-200"
COLOR_300 = f"{COLOR_BASE}-300"
COLOR_400 = f"{COLOR_BASE}-400"
COLOR_900 = f"{COLOR_BASE}-900"
COLOR_BRAND_1 = "blue-700"
COLOR_BRAND_2 = "fuchsia-600"
COLOR_BRAND_2_LIGHT = "fuchsia-500"
BUTTON_SHAPE = "p-3 rounded-md font-semibold cursor-pointer shadow-lg active:shadow-none"
BUTTON_PRIMARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_BRAND_1} to-{COLOR_BRAND_2} text-{COLOR_100} hover:to-{COLOR_BRAND_2_LIGHT}"
BUTTON_SECONDARY = f"{BUTTON_SHAPE} bg-linear-to-tr from-{COLOR_400} to-{COLOR_300} text-{COLOR_900} hover:to-{COLOR_200}"
PAGE = f"min-h-screen bg-{COLOR_900} flex justify-center items-center"
CARD = "max-w-2xl mx-auto p-6 space-y-6 bg-white rounded-xl shadow-md"
TEXT_CONTAINER = "w-full flex flex-grow p-6 rounded-lg bg-white justify-center items-center"


# --- State Instances ---
# State to track which content variant is shown on page 1
content_state = State("a", "content_state")


# --- Trigger Handler ---
@app.trigger_handler
def switch_content():
    """Toggle between content variants a and b."""
    current = content_state.get()
    new = "b" if current == "a" else "a"
    content_state.set(new)
    return update_components(*content_state.listeners)


# --- Component Functions ---
def PageHeader(title: str, color: str = "black") -> Text:  # noqa: N802
    """Return a page header with the given title."""
    return Text(title, css=f"text-3xl font-bold mb-6 text-center text-{color}")


def Divider(color: str) -> Div:  # noqa: N802
    """Return a horizontal divider."""
    return Div(
        Div("", css=f"border-t border-{color}/20 flex-1"),
        Text("OR", css=f"text-center font-semibold text-{color}"),
        Div("", css=f"border-t border-{color}/20 flex-1"),
        css="w-full flex flex-row items-center gap-3",
    )


def SwitchPageButton(href: str, label: str):  # noqa: N802
    """Return a button that navigates to a different page."""
    return Link(
        Button(
            label,
            css=f"{BUTTON_PRIMARY} w-full",
        ),
        href=href,
        css="block",
    )


def SwitchContentButton():  # noqa: N802
    """Return a button that switches content on the same page."""
    return Button(
        "Switch Content",
        trigger="switch_content",
        css=f"{BUTTON_SECONDARY} w-full",
    )


def ContentA():  # noqa: N802
    """Return content variant A."""
    return Div(
        PageHeader("Page 1 - Content A"),
        # Hint for traditional navigation
        Text(
            "Click 'Go to Page 2' below to navigate to Page 2. "
            "Watch how the URL in your browser's address bar changes."
        ),
        # Link for traditional navigation (URL changes)
        SwitchPageButton(href="/page2", label="Go to Page 2"),
        Divider(color="black"),
        # Hint for SPA content switching
        Text(
            "Click 'Switch Content' below to change the content on this page. "
            "Notice how the content changes but the URL stays the same."
        ),
        # Button for SPA content switching (URL stays)
        SwitchContentButton(),
        css=CARD,
    )


def ContentB():  # noqa: N802
    """Return content variant B."""
    return Div(
        PageHeader("Page 1 - Content B", color="white"),
        Div(SwitchPageButton(href="/page2", label="Go to Page 2"), SwitchContentButton(), css="grid grid-cols-2 gap-6"),
        Div(
            Text(
                "Click 'Go to Page 2' to navigate to Page 2. Watch how the URL in your browser's address bar changes.",
                css="text-center",
            ),
            css=TEXT_CONTAINER,
        ),
        Divider(color="white"),
        Div(
            Text(
                "Click 'Switch Content' to change the content on this page. "
                "Notice how the content changes but the URL stays the same.",
                css="text-center",
            ),
            css=TEXT_CONTAINER,
        ),
        css="max-w-6xl min-h-screen mx-auto p-6 space-y-6 flex flex-col",
    )


# --- Page Component Functions ---
def Page1():  # noqa: N802
    """Page 1 demonstrating traditional navigation and SPA content switching."""
    return Div(
        dynamic(ContentA() if content_state.get() == "a" else ContentB()),
        css=PAGE,
        listen_to="content_state",
    )


def Page2():  # noqa: N802
    """Page 2 demonstrating traditional navigation and SPA content switching."""
    return Div(
        Div(
            PageHeader("Page 2"),
            # Hint for traditional navigation
            Text(
                "Click 'Go to Page 1' below to navigate to Page 1. "
                "Watch how the URL in your browser's address bar changes."
            ),
            # Link for traditional navigation (URL changes)
            SwitchPageButton(href="/page1", label="Go to Page 1"),
            css=CARD,
        ),
        css=PAGE,
    )


# --- Routes ---
@app.page("/")
def index():
    """Redirect to Page 1."""
    return redirect("/page1")


@app.page("/page1")
def page1():
    """Render Page 1."""
    return Page1()


@app.page("/page2")
def page2():
    """Render Page 2."""
    return Page2()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.navigation_demo:app", host="0.0.0.0", port=8000, reload=True)
