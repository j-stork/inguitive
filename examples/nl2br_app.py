"""
nl2br utility example using inguitive.

Run with: uvicorn examples.nl2br_app:app --reload

Newline-to-<br> Conversion (safe by default)
--------------------------------------------
This example demonstrates the ``nl2br`` helper, which converts newline
characters (``\n``, ``\r\n``, ``\r``) in a string to ``<br>`` tags so that
multiline text entered in a ``<textarea>`` renders with line breaks in HTML.

``nl2br`` is safe to call on untrusted user input: it escapes HTML-special
characters (``<``, ``>``, ``&``, ``"``, ``'``) via ``markupsafe.escape``
before converting newlines, and returns a ``markupsafe.Markup`` so the
framework emits the result as HTML without re-escaping the ``<br>`` tags.
Callers no longer need to wrap the input in
``Markup(nl2br(str(escape(content))))`` — ``nl2br(content)`` is enough.

Here the handler stores the submitted text in ``text_state``; the display
panel calls ``nl2br(content)`` directly. Submitting

    <script>
        Some pseudo code
        with line break
    </script>

renders as

    &lt;script&gt;
        Some pseudo code<br>
        with line break
    &lt;/script&gt;

The angle brackets are escaped (no script executes) and only the newlines
become ``<br>`` tags.

Three panels show the difference side by side: the "Text as entered"
panel renders the submitted text with no conversion (newlines collapse to
spaces), the "Converted text" panel applies ``nl2br`` (newlines become
``<br>``), and the "Raw converted markup" panel shows the literal HTML
string ``nl2br`` produced (``&lt;script&gt;<br>...``), so the escaping is
visible without viewing page source.

To test:
1. Type multiline text into the box (use Enter for line breaks)
2. Submit — the panel below shows the text with real line breaks
3. View source: the newlines have become <br> tags, not escaped text
4. Submit text containing ``<script>…</script>`` — the angle brackets are
   escaped (``&lt;script&gt;``) and only the newlines become ``<br>``,
   which is the safe pattern shown here.
"""

from collections.abc import Callable

from fastapi import FastAPI, Request

from inguitive import Button, Div, Form, State, Text, Textarea, UI, get_form_data, nl2br

from .css import BUTTON_PRIMARY_GREEN_CSS, INPUT_CSS, TEXT_CSS
from .custom_components import BaseContainer, Card, HorizontalRule, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- State Instances ---
# Holds the last submitted text. None until the first submit.
text_state = State(None, "text_state")


# --- Trigger Handlers ---
@ui.trigger_handler
async def submit(request: Request):
    """Store the submitted text for display."""
    form_data = await get_form_data(request)
    text_state.set(form_data.get("content", ""))
    # No return: auto-propagation re-renders the display panel.


# --- Components ---
def TextDisplay(header_text: str, dynamic_text_func: Callable[[], str]) -> Div:  # noqa: N802
    """Return a Div that displays the text from the given callable."""
    return Div(
        Title(header_text, level=2),
        Text(
            dynamic_text_func,
            listen_to=text_state,
            css=f"text-center {TEXT_CSS}",
        ),
        css="space-y-6",
    )


def TextForm() -> Div:  # noqa: N802
    def dynamic_plain_text() -> str:
        """Return the submitted text unchanged, for the 'before' panel.

        The plain string is escaped by ``Text._resolve`` (safe on untrusted
        input), and the browser collapses the newlines to spaces because no
        ``<br>`` tags are present — showing what the text looks like before
        ``nl2br`` is applied.
        """
        content = text_state.get()
        if not content:
            return ""
        return content

    def dynamic_nl2br_text() -> str:
        """Render the stored text with newlines converted to <br> tags.

        ``nl2br`` escapes HTML-special characters and returns a ``Markup``, so
        this is safe on untrusted input — no manual ``escape``/``str``/``Markup``
        chain is needed.
        """
        content = text_state.get()
        if not content:
            return ""
        return nl2br(content)

    def dynamic_raw_text() -> str:
        """Return the nl2br output as a plain str for literal display.

        ``nl2br`` returns a ``markupsafe.Markup``. Wrapping it in ``str()``
        strips the Markup type so ``Text._resolve`` escapes it again, and the
        browser displays the literal ``&lt;script&gt;<br>...`` characters
        instead of rendering them — making the escaping ``nl2br`` applied
        visible without viewing page source.
        """
        content = text_state.get()
        if not content:
            return ""
        return str(nl2br(content))

    return BaseContainer(
        InguitiveLogo(),
        Title("Newline-to-<br> Conversion Example"),
        Card(
            Form(
                Textarea(
                    id="content",
                    placeholder="Type multiple lines,\nuse Enter for line breaks",
                    rows=4,
                    css=INPUT_CSS,
                ),
                Button(
                    "Submit",
                    type="submit",
                    css=f"{BUTTON_PRIMARY_GREEN_CSS} w-full",
                ),
                trigger=submit,
                css="space-y-6",
            ),
        ),
        TextDisplay("Text as entered (no conversion):", dynamic_plain_text),
        HorizontalRule(),
        TextDisplay("Converted text:", dynamic_nl2br_text),
        HorizontalRule(),
        TextDisplay("Raw converted markup:", dynamic_raw_text),
    )


# --- Routes ---
@app.get("/")
def home():
    return ui.page(TextForm())


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.nl2br_app:app", host="0.0.0.0", port=8000, reload=True)
