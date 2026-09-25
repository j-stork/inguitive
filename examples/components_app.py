"""
Component showcase example using inguitive.

Run with: uvicorn examples.components_app:app --reload

A static app that displays all available inguitive components one below
the other. No reactivity — this is a visual reference for the component
library. We'll add reactivity later.
"""

from fastapi import FastAPI

from inguitive import (
    UI,
    Anchor,
    Button,
    Checkbox,
    DataTable,
    Div,
    Form,
    Header,
    Icon,
    Image,
    Input,
    Label,
    Radio,
    Select,
    TemplateComponent,
    Text,
    Textarea,
)

# --- App Setup ---
app = FastAPI()
ui = UI(app)

# A small inline SVG for the Icon demo.
_CHECK_SVG = (
    '<svg viewBox="0 0 20 20" fill="currentColor">'
    '<path d="M16.7 5.3a1 1 0 0 1 0 1.4l-7 7a1 1 0 0 1-1.4 0l-3-3'
    'a1 1 0 1 1 1.4-1.4L9 11.6l6.3-6.3a1 1 0 0 1 1.4 0z"/>'
    '</svg>'
)

_TABLE_DATA = [
    {"name": "Alice", "role": "Engineer"},
    {"name": "Bob", "role": "Designer"},
]


# --- Custom component ---
def IsRenderedTo(tag: str) -> Text:  # noqa: N802
    return Text(tag, css="font-mono text-gray-600")


# --- Routes ---
@app.get("/")
def home():
    return ui.page(
        Div(
            # Text
            Header("Component Showcase", level=1, css="col-span-2 text-2xl font-bold"),
            Header("Component", level=2, css="text-xl font-semibold border-b"),
            Header("is rendered to:", level=2, css="text-xl font-semibold border-b"),

            Div("Div", css="px-4 py-8 border text-center text-gray-400"),
            IsRenderedTo("<div>"),

            Text("Text component — a paragraph of text."),
            IsRenderedTo("<p>"),

            # Header levels
            Header("Header level 1", level=1, css="text-2xl"),
            IsRenderedTo("<h1>"),
            Header("Header level 2", level=2, css="text-xl"),
            IsRenderedTo("<h2>"),
            Header("Header level 3", level=3, css="text-lg"),
            IsRenderedTo("<h3>"),

            # Button
            Button("Button", css="px-3 py-2 bg-blue-500"),
            IsRenderedTo("<button>"),

            # Anchor
            Anchor("Anchor link", href="#"),
            IsRenderedTo("<a>"),

            # Image
            Image(src="https://placehold.co/150x50", alt="Placeholder", css="h-12"),
            IsRenderedTo("<img>"),

            # Icon
            Icon(_CHECK_SVG, css="w-6 h-6 text-green-500"),
            IsRenderedTo("<svg>"),

            # Label
            Label("Label for input", for_="demo-input"),
            IsRenderedTo("<label>"),

            # Input
            Input(id="demo-input", placeholder="Type here", css="border p-2"),
            IsRenderedTo("<input>"),

            # Textarea
            Textarea(id="demo-textarea", placeholder="Multi-line text", rows=3, css="border p-2"),
            IsRenderedTo("<textarea>"),

            # Select
            Select(
                id="demo-select",
                options=[("a", "Option A"), ("b", "Option B")],
                css="border p-2",
            ),
            IsRenderedTo("<select>"),

            # Checkbox
            Div(
                Checkbox(id="demo-checkbox", checked=True),
                Label("Checkbox", for_="demo-checkbox"),
                css="flex items-center gap-2",
            ),
            IsRenderedTo('<input type="checkbox">'),

            # Radio
            Div(
                Radio(id="demo-radio-1", name="demo-radio", value="yes", checked=True),
                Label("Yes", for_="demo-radio-1"),
                Radio(id="demo-radio-2", name="demo-radio", value="no"),
                Label("No", for_="demo-radio-2"),
                css="flex items-center gap-4",
            ),
            IsRenderedTo('<input type="radio">'),

            # Form
            Form(
                Input(id="form-input", placeholder="Form input", css="border p-2"),
                Button("Submit", type="submit", css="px-3 py-2 bg-green-500"),
                css="flex flex-col gap-4 p-4 border shadow-lg",
            ),
            IsRenderedTo("<form>"),

            # DataTable
            DataTable(data=_TABLE_DATA, css="w-full border"),
            IsRenderedTo("<table>"),

            # TemplateComponent
            TemplateComponent(
                template='<div class="border p-4">Template: {{ message }}</div>',
                message="Rendered via Jinja2",
            ),
            IsRenderedTo("Depends on the template"),

            css="grid grid-cols-2 gap-6 p-6 max-w-4xl mx-auto",
        )
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.components_app:app", host="0.0.0.0", port=8000, reload=True)
