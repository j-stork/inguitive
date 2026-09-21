"""
URL path parameters example using inguitive.

Run with: uvicorn examples.url_params_app:app --reload

Dynamic Path Segments: FastAPI {name} + type annotations
--------------------------------------------------------
This example demonstrates FastAPI's URL path parameter syntax (used directly
via ``@app.get``). A route pattern contains segments like ``{item_id}`` or
``{subpath:path}``; the handler's type annotation (``item_id: int``) tells
FastAPI how to parse and validate the segment, and it passes the typed value
to the handler as an argument.

Three routes exercise the main type behaviours:

| Route                         | Segment type | Behaviour                                  |
|-------------------------------|--------------|--------------------------------------------|
| ``/item/{item_id}``           | ``int``      | Coerces to int; ``/item/abc`` returns 422  |
| ``/user/{username}``          | ``str``      | Default type when none is given             |
| ``/files/{subpath:path}``    | ``path``     | Preserves slashes, captures the rest       |

The index page links to a concrete example of each so you can see the parsed
value reflected back. Mismatched types (e.g. ``/item/not-a-number``) produce
an HTTP 422 with a descriptive detail, which is FastAPI's built-in
validation for path parameters — no handler code needed.

Contrast with ``routing_app.py``, which uses only static paths and
``RedirectResponse``, and with ``trigger_args_app.py``, where per-request data flows
through query parameters on a POST rather than the URL path.

To test:
1. Visit ``/`` — three links are shown
2. Click "Item 42" — goes to ``/item/42``, shows "Item ID: 42"
3. Click "User ada" — goes to ``/user/ada``, shows "Username: ada"
4. Click "Files a/b/c.txt" — goes to ``/files/a/b/c.txt``, shows the whole path
5. Manually visit ``/item/abc`` — returns 422 (invalid int)
"""

from fastapi import FastAPI

from inguitive import UI, Anchor, Div, Text

from .css import BRAND_COLORS, LINK_CSS
from .custom_components import BaseContainer, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- Components ---
def PageContainer(*content) -> Div:  # noqa: N802
    """A reusable page component for all pages."""
    return BaseContainer(
        InguitiveLogo(),
        Title("URL Path Parameters Example"),
        *content,
    )


def PageContent(label: str, value: object) -> Div:  # noqa: N802
    """A reusable page that reflects a parsed path parameter back to the visitor.

    The three parameter routes below differ only in the label they print and the
    value they receive, so they all delegate here for the markup.
    """
    return PageContainer(
        Text(f"{label}: {value}", css=f"text-{BRAND_COLORS['green']}"),
        Text(f"Parsed type: {type(value).__name__}", css=f"text-{BRAND_COLORS['yellow']}"),
        Anchor("Back", href="/", css=LINK_CSS),
    )


# --- Routes ---
@app.get("/")
def index():
    return ui.page(PageContainer(
        Anchor("Item 42", href="/item/42", css=LINK_CSS),
        Anchor("User ada", href="/user/ada", css=LINK_CSS),
        Anchor("Files a/b/c.txt", href="/files/a/b/c.txt", css=LINK_CSS),
        Text(
            "Try /item/abc to see the 422 from a failed int parse.",
            css=f"text-{BRAND_COLORS['red']}",
        ),
    ))


@app.get("/item/{item_id}")
def item(item_id: int):
    """``int`` segment — coerced and validated; bad input returns 422."""
    return ui.page(PageContent("Item ID", item_id))


@app.get("/user/{username}")
def user_profile(username: str):
    """No type given — defaults to ``str``."""
    return ui.page(PageContent("Username", username))


@app.get("/files/{subpath:path}")
def files(subpath: str):
    """``path`` segment — captures the rest of the URL including slashes."""
    return ui.page(PageContent("File path", subpath))


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.url_params_app:app", host="0.0.0.0", port=8000, reload=True)
