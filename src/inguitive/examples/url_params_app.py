"""
URL path parameters example using inguitive.

Run with: uvicorn inguitive.examples.url_params_app:app --reload

Dynamic Path Segments: <name:type>
---------------------------------
This example demonstrates inguitive's URL path parameter syntax. A route
pattern contains segments like ``<id:int>`` or ``<filepath:path>``; when a
request matches, inguitive parses the segment into the declared Python type
and passes it to the page handler as a typed argument.

Three routes exercise the main type behaviours:

| Route                         | Segment type | Behaviour                                  |
|-------------------------------|--------------|--------------------------------------------|
| ``/item/<item_id:int>``       | ``int``      | Coerces to int; ``/item/abc`` returns 400  |
| ``/user/<username>``          | ``str``      | Default type when none is given             |
| ``/files/<subpath:path>``    | ``path``     | Preserves slashes, captures the rest       |

The index page links to a concrete example of each so you can see the parsed
value reflected back. Mismatched types (e.g. ``/item/not-a-number``) produce
an HTTP 400 with a descriptive detail, which is the framework's built-in
validation for path parameters — no handler code needed.

Contrast with ``routing_app.py``, which uses only static paths and
``redirect``, and with ``trigger_args_app.py``, where per-request data flows
through query parameters on a POST rather than the URL path.

To test:
1. Visit ``/`` — three links are shown
2. Click "Item 42" — goes to ``/item/42``, shows "Item ID: 42"
3. Click "User ada" — goes to ``/user/ada``, shows "Username: ada"
4. Click "Files a/b/c.txt" — goes to ``/files/a/b/c.txt``, shows the whole path
5. Manually visit ``/item/abc`` — returns 400 (invalid int)
"""

from inguitive import Div, Link, Text, create_app

from .css import BRAND_COLORS, LINK_CSS
from .custom_components import BaseContainer, InguitiveLogo, Title

# --- App Setup ---
app = create_app()


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
        Link("Back", href="/", css=LINK_CSS),
    )


# --- Routes ---
@app.page("/")
def index():
    return PageContainer(
        Link("Item 42", href="/item/42", css=LINK_CSS),
        Link("User ada", href="/user/ada", css=LINK_CSS),
        Link("Files a/b/c.txt", href="/files/a/b/c.txt", css=LINK_CSS),
        Text(
            "Try /item/abc to see the 400 from a failed int parse.",
            css=f"text-{BRAND_COLORS['red']}",
        ),
    )


@app.page("/item/<item_id:int>")
def item(item_id: int):
    """``int`` segment — coerced and validated; bad input returns 400."""
    return PageContent("Item ID", item_id)


@app.page("/user/<username>")
def user_profile(username: str):
    """No type given — defaults to ``str``."""
    return PageContent("Username", username)


@app.page("/files/<subpath:path>")
def files(subpath: str):
    """``path`` segment — captures the rest of the URL including slashes."""
    return PageContent("File path", subpath)


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.url_params_app:app", host="0.0.0.0", port=8000, reload=True)
