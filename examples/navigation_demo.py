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
# State to track which content variant is shown on each page
page1_content_state = State("variant_a", "page1_content")
page2_content_state = State("variant_a", "page2_content")


# --- Trigger Handlers ---
@app.trigger_handler
def switch_page1_content():
    """Toggle between content variants on Page 1."""
    current = page1_content_state.get()
    new_variant = "variant_b" if current == "variant_a" else "variant_a"
    page1_content_state.set(new_variant)
    return update_components(*page1_content_state.listeners)


@app.trigger_handler
def switch_page2_content():
    """Toggle between content variants on Page 2."""
    current = page2_content_state.get()
    new_variant = "variant_b" if current == "variant_a" else "variant_a"
    page2_content_state.set(new_variant)
    return update_components(*page2_content_state.listeners)


# --- Helper Functions for Content Variants ---
def get_page1_content():
    """Return the content area for Page 1 based on current state."""
    variant = page1_content_state.get()
    if variant == "variant_a":
        return [
            Div(
                Text("This is Content Variant A on Page 1", css="text-lg font-medium"),
                css="p-4 bg-blue-100 rounded-lg border-2 border-blue-300",
            )
        ]
    else:
        return [
            Div(
                Text("This is Content Variant B on Page 1", css="text-lg font-medium"),
                css="p-4 bg-green-100 rounded-lg border-2 border-green-300",
            )
        ]


def get_page2_content():
    """Return the content area for Page 2 based on current state."""
    variant = page2_content_state.get()
    if variant == "variant_a":
        return [
            Div(
                Text("This is Content Variant A on Page 2", css="text-lg font-medium"),
                css="p-4 bg-purple-100 rounded-lg border-2 border-purple-300",
            )
        ]
    else:
        return [
            Div(
                Text("This is Content Variant B on Page 2", css="text-lg font-medium"),
                css="p-4 bg-orange-100 rounded-lg border-2 border-orange-300",
            )
        ]


# --- Page Component Functions ---
def Page1():
    """Page 1 demonstrating traditional navigation and SPA content switching."""
    return Div(
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
            lambda: get_page1_content(),
            id="page1_content",
            listen_to="page1_content",
            css="mb-6",
        ),
        
        # Button for SPA content switching (URL stays)
        Button(
            "Switch Content",
            trigger="switch_page1_content",
            css="w-full p-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors",
        ),
        
        css="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-md",
    )


def Page2():
    """Page 2 demonstrating traditional navigation and SPA content switching."""
    return Div(
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
        
        # Content area that will change
        Div(
            lambda: get_page2_content(),
            id="page2_content",
            listen_to="page2_content",
            css="mb-6",
        ),
        
        # Button for SPA content switching (URL stays)
        Button(
            "Switch Content",
            trigger="switch_page2_content",
            css="w-full p-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors",
        ),
        
        css="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-md",
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
