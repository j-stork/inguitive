"""
nl2br utility example using inguitive.

Run with: uvicorn inguitive.examples.nl2br_app:app --reload

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

A second "Raw converted markup" panel shows the literal HTML string that
``nl2br`` produced (``&lt;script&gt;<br>...``), so the escaping is visible
without viewing page source.

To test:
1. Type multiline text into the box (use Enter for line breaks)
2. Submit — the panel below shows the text with real line breaks
3. View source: the newlines have become <br> tags, not escaped text
4. Submit text containing ``<script>…</script>`` — the angle brackets are
   escaped (``&lt;script&gt;``) and only the newlines become ``<br>``,
   which is the safe pattern shown here.
"""

from inguitive import Button, Div, Form, Header, State, Text, Textarea, create_app, nl2br

from .css import BASE_CONTAINER_CSS, BUTTON_PRIMARY_CSS, CARD_CONTAINER_CSS, HEADER_CSS, INPUT_CSS

# --- App Setup ---
app = create_app()


# --- State Instances ---
# Holds the last submitted text. None until the first submit.
text_state = State(None, "text_state")


# --- Trigger Handlers ---
@app.trigger_handler
def submit(form_data: dict):
    """Store the submitted text for display."""
    text_state.set(form_data.get("content", ""))
    # No return: auto-propagation re-renders the display panel.


# --- Components ---
def TextForm() -> Div:  # noqa: N802
    def dynamic_text() -> str:
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

    return Div(
        Header("Newline-to-<br> Conversion Example", css=HEADER_CSS),
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
                css=f"{BUTTON_PRIMARY_CSS} w-full",
            ),
            trigger="submit",
            css=CARD_CONTAINER_CSS,
        ),
        Text("Converted text:", css="text-lg text-center text-white"),
        Text(
            dynamic_text,
            listen_to="text_state",
            css="text-center text-white",
        ),
        Text("Raw converted markup:", css="text-lg text-center text-white mt-6"),
        Text(
            dynamic_raw_text,
            listen_to="text_state",
            css="text-center text-white font-mono text-sm break-all",
        ),
        css=BASE_CONTAINER_CSS,
    )


# --- Routes ---
@app.page("/")
def home():
    return TextForm()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.nl2br_app:app", host="0.0.0.0", port=8000, reload=True)
