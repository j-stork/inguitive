"""
nl2br utility example using inguitive.

Run with: uvicorn examples.nl2br_app:app --reload

Demonstrates the ``nl2br`` helper, which converts newline characters in
a string to ``<br>`` tags so that multiline text renders with line breaks
in HTML. The same fixed text is displayed twice: once without ``nl2br``
(newlines collapse to spaces in the browser) and once with ``nl2br``
(newlines become ``<br>`` tags).
"""

from fastapi import FastAPI

from inguitive import UI, Div, Header, Text, nl2br

# --- App Setup ---
app = FastAPI()
ui = UI(app)

# A fixed, multi-line string defined as a constant.
SAMPLE_TEXT = (
    "First line of text.\n"
    "Second line of text.\n"
    "Third line of text."
)


# --- Routes ---
@app.get("/")
def home():
    return ui.page(
        Div(
            Header("nl2br Example", level=1, css="text-2xl"),

            # Without nl2br: newlines collapse to spaces in the browser.
            Header("Without nl2br", level=2, css="text-lg"),
            Text(SAMPLE_TEXT, css="whitespace-pre-wrap"),

            # With nl2br: newlines are converted to <br> tags.
            Header("With nl2br", level=2, css="text-lg"),
            Text(nl2br(SAMPLE_TEXT)),

            css="flex flex-col gap-6 p-6 max-w-2xl mx-auto",
        )
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.nl2br_app:app", host="0.0.0.0", port=8000, reload=True)
