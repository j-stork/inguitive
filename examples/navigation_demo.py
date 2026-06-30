"""
Navigation Demo example using INGUITIVE framework.

Demonstrates two approaches to navigation:
1. Traditional multi-page navigation (URL changes)
2. SPA-style content switching (URL stays constant, content changes)

Run with: uvicorn examples.navigation_demo:app --reload
"""

from pathlib import Path

from inguitive import Button, Div, Link, State, Text, create_app, redirect, update_components

# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent / "templates")


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


# --- Helper Function for Content Variants ---
def get_content():
    """Return the content area based on current state."""
    variant = content_state.get()
    css_text = "text-lg font-medium text-center"
    css_div = "w-full p-6 rounded-lg border-2"
    if variant == "a":
        return Div(
            Text("This is Content Variant A", css=f"{css_text} text-blue-800"),
            css=f"{css_div} bg-blue-100 border-blue-300",
        )
    else:
        return Div(
            Text("This is Content Variant B", css=f"{css_text} text-green-800"),
            css=f"{css_div} bg-green-100 border-green-300",
        )


# --- Page Component Functions ---
def Page1():
    """Page 1 demonstrating traditional navigation and SPA content switching."""
    return Div(
        Div(
            Text("Page 1", css="text-3xl font-bold mb-6 text-center"),
            # Hint for traditional navigation
            Text(
                "Click 'Go to Page 2' below to navigate to Page 2. "
                "Watch how the URL in your browser's address bar changes.",
                css="mb-4 text-gray-700",
            ),
            # Link for traditional navigation (URL changes)
            Link(
                "Go to Page 2",
                href="/page2",
                css="block w-full p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors mb-6 text-center no-underline",
            ),
            Div(
                Text("OR", css="text-center font-semibold text-gray-500 mb-6"),
            ),
            # Hint for SPA content switching
            Text(
                "Click 'Switch Content' below to change the content on this page. "
                "Notice how the content changes but the URL stays the same.",
                css="mb-4 text-gray-700",
            ),
            # Content area that will change
            Div(
                lambda: get_content(),
                id="content_state",
                listen_to="content_state",
                css="mb-6",
            ),
            # Button for SPA content switching (URL stays)
            Button(
                "Switch Content",
                trigger="switch_content",
                css="w-full p-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors",
            ),
            css="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-md",
        ),
        css="min-h-screen flex justify-center items-center bg-slate-900"
    )


def Page2():
    """Page 2 demonstrating traditional navigation and SPA content switching."""
    return Div(
        Div(
            Text("Page 2", css="text-3xl font-bold mb-6 text-center"),
            # Hint for traditional navigation
            Text(
                "Click 'Go to Page 1' below to navigate to Page 1. "
                "Watch how the URL in your browser's address bar changes.",
                css="mb-4 text-gray-700",
            ),
            # Link for traditional navigation (URL changes)
            Link(
                "Go to Page 1",
                href="/page1",
                css="block w-full p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors mb-6 text-center no-underline",
            ),
            Div(
                Text("OR", css="text-center font-semibold text-gray-500 mb-6"),
            ),
            # Hint for SPA content switching
            Text(
                "Click 'Switch Content' below to change the content on this page. "
                "Notice how the content changes but the URL stays the same.",
                css="mb-4 text-gray-700",
            ),
            css="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-md",
        ),
        css="min-h-screen flex justify-center items-center bg-slate-900"
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
