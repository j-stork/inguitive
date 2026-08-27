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

# --- App Setup ---
app = create_app()


# --- Routes ---
@app.page("/")
def index():
    return Div(
        Text("URL Path Parameters", css="text-2xl font-bold text-slate-900"),
        Link("Item 42", href="/item/42", css="block text-blue-600 underline"),
        Link("User ada", href="/user/ada", css="block text-blue-600 underline"),
        Link("Files a/b/c.txt", href="/files/a/b/c.txt", css="block text-blue-600 underline"),
        Text(
            "Try /item/abc to see the 400 from a failed int parse.",
            css="text-sm text-slate-500",
        ),
        css="max-w-md mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg space-y-3",
    )


@app.page("/item/<item_id:int>")
def item(item_id: int):
    """``int`` segment — coerced and validated; bad input returns 400."""
    return Div(
        Text(f"Item ID: {item_id}", css="text-xl text-slate-900"),
        Text(f"Parsed type: {type(item_id).__name__}", css="text-sm text-slate-500"),
        Link("Back", href="/", css="block text-blue-600 underline"),
        css="max-w-md mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg space-y-2",
    )


@app.page("/user/<username>")
def user_profile(username: str):
    """No type given — defaults to ``str``."""
    return Div(
        Text(f"Username: {username}", css="text-xl text-slate-900"),
        Text(f"Parsed type: {type(username).__name__}", css="text-sm text-slate-500"),
        Link("Back", href="/", css="block text-blue-600 underline"),
        css="max-w-md mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg space-y-2",
    )


@app.page("/files/<subpath:path>")
def files(subpath: str):
    """``path`` segment — captures the rest of the URL including slashes."""
    return Div(
        Text(f"File path: {subpath}", css="text-xl text-slate-900"),
        Text(f"Parsed type: {type(subpath).__name__}", css="text-sm text-slate-500"),
        Link("Back", href="/", css="block text-blue-600 underline"),
        css="max-w-md mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg space-y-2",
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.url_params_app:app", host="0.0.0.0", port=8000, reload=True)
