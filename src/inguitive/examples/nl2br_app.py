"""
nl2br utility example using inguitive.

Run with: uvicorn inguitive.examples.nl2br_app:app --reload

Newline-to-<br> Conversion
-------------------------
This example demonstrates the ``nl2br`` helper, which converts newline
characters (``\n``, ``\r\n``, ``\r``) in a string to ``<br>`` tags so that
multiline text entered in a ``<textarea>`` renders with line breaks in HTML.

The subtlety it highlights is the interaction with HTML escaping. ``nl2br``
only converts newlines — it does not strip or escape ``<script>`` or other
HTML tags. To use it safely on user input, escape the text **first**, then
convert newlines, then wrap the result in ``markupsafe.Markup`` so the
framework's escaping does not re-escape the ``<br>`` tags it just produced:

    Markup(nl2br(str(markupsafe.escape(content))))

The order matters: escaping first turns ``<`` and ``>`` into ``&lt;`` and
``&gt;`` (neutralising any HTML the user typed), then ``nl2br`` turns the
newlines into ``<br>`` tags, then ``Markup`` tells the framework the
resulting string is safe to emit as HTML. The ``str()`` around ``escape``
is needed because ``markupsafe.escape`` returns a ``Markup`` object whose
``.replace()`` (used inside ``nl2br``) would otherwise re-escape the
inserted ``<br>``. Reversing the escape/nl2br order would let user-supplied
``<script>`` tags through verbatim — an XSS hole.

Here the handler stores the submitted text in ``text_state``; the display
panel applies the safe sequence above. Submitting

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

To test:
1. Type multiline text into the box (use Enter for line breaks)
2. Submit — the panel below shows the text with real line breaks
3. View source: the newlines have become <br> tags, not escaped text
4. Submit text containing ``<script>…</script>`` — the angle brackets are
   escaped (``&lt;script&gt;``) and only the newlines become ``<br>``,
   which is the safe pattern shown here.
"""

from markupsafe import Markup, escape

from inguitive import Button, Div, Form, State, Text, Textarea, create_app, nl2br

from .css import BUTTON_PRIMARY_CSS

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
def display_text() -> str:
    """Render the stored text with newlines converted to <br> tags.

    The safe sequence is escape → nl2br → Markup: escaping first neutralises
    any HTML the user typed, then ``nl2br`` turns newlines into ``<br>``
    tags, then ``Markup`` tells the framework the result is safe to emit
    (so the ``<br>`` tags are not re-escaped).

    The ``str()`` around ``escape()`` is deliberate: ``markupsafe.escape``
    returns a ``Markup`` object, and ``Markup.replace`` (used inside
    ``nl2br``) re-escapes the inserted ``<br>`` string — yielding
    ``&lt;br&gt;`` instead of ``<br>``. Converting to a plain ``str`` first
    keeps ``nl2br``'s replacement literal.
    """
    content = text_state.get()
    if not content:
        return ""
    return Markup(nl2br(str(escape(content))))


def Display() -> Div:  # noqa: N802
    return Div(
        Text(display_text, listen_to="text_state", css="whitespace-pre-wrap text-slate-900"),
        css="max-w-md mx-auto mt-6 p-4 bg-slate-100 rounded-lg min-h-24",
    )


def TextForm() -> Div:  # noqa: N802
    return Div(
        Form(
            Textarea(id="content", placeholder="Type multiple lines…\nuse Enter for line breaks", rows=4),
            Button("Submit", type="submit", css=f"{BUTTON_PRIMARY_CSS} w-full"),
            trigger="submit",
            css="space-y-3 max-w-md mx-auto p-6 bg-white rounded-xl shadow-md",
        ),
        Display(),
        css="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50",
    )


# --- Routes ---
@app.page("/")
def home():
    return TextForm()


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.nl2br_app:app", host="0.0.0.0", port=8000, reload=True)
