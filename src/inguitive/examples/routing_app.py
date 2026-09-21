"""
Multi-page routing example using inguitive.

Run with: uvicorn inguitive.examples.routing_app:app --reload

Routing: @app.get + ui.page, RedirectResponse, and Anchor
---------------------------------------------------------
This example demonstrates three pieces of inguitive's routing layer:

1. **Multiple pages via ``@app.get`` + ``ui.page()``.** Each ``@app.get("/path")``
   decorator registers a FastAPI GET route; the handler returns
   ``ui.page(component)`` to wrap the component in the HTML shell. Here
   ``/page1`` and ``/page2`` are two distinct pages with their own URLs.

2. **``RedirectResponse`` for URL-level navigation.** The root path ``/`` returns
   ``RedirectResponse("/page1")``, which issues an HTTP 302 so the browser's
   address bar updates to the target URL. This is the "URL changes" model — a
   real page transition, not an in-place content swap.

3. **``Anchor`` for anchor navigation.** ``Anchor`` renders an ``<a>`` tag whose
   ``href`` points at another route. Clicking it triggers a normal browser
   navigation, so the URL changes and the matching ``@app.get`` handler
   renders.

Contrast with ``counter_app.py`` and the trigger-handler apps, where
interactions stay on a single page and update content via HTMX OOB swaps
without a URL change.

To test:
1. Visit ``/`` — the browser redirects to ``/page1`` (address bar updates)
2. Click "Go to Page 2" — the URL changes to ``/page2``
3. Click "Back to Page 1" — the URL changes back to ``/page1``
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from inguitive import Div, Anchor, Text, UI

from .css import BUTTON_PRIMARY_BLUE_CSS, BUTTON_PRIMARY_YELLOW_CSS, TEXT_CSS
from .custom_components import BaseContainer, Card, InguitiveLogo, Title

# --- App Setup ---
app = FastAPI()
ui = UI(app)


# --- Components ---
def PageContainer(page_title: str, page_text: str, link_label: str, href: str) -> Div:  # noqa: N802
    """A simple and reusable page shell."""
    if href == "/page1":
        link_css = BUTTON_PRIMARY_YELLOW_CSS
    else:
        link_css = BUTTON_PRIMARY_BLUE_CSS

    return BaseContainer(
        InguitiveLogo(),
        Title("Routing Example"),
        Card(
            Title(page_title, level=2),
            Text(page_text, css=TEXT_CSS),
            Anchor(
                link_label,
                href=href,
                css=link_css,
            ),
        ),
    )


# --- Routes ---
@app.get("/")
def root():
    """Redirect the bare root path to /page1."""
    return RedirectResponse("/page1", status_code=302)


@app.get("/page1")
def home():
    return ui.page(PageContainer(
        page_title="Page 1",
        page_text="This is page 1. The URL is /page1.",
        link_label="Go to Page 2",
        href="/page2",
    ))


@app.get("/page2")
def about():
    return ui.page(PageContainer(
        page_title="Page 2",
        page_text="This is page 2. The URL is /page2.",
        link_label="Back to Page 1",
        href="/page1",
    ))


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.routing_app:app", host="0.0.0.0", port=8000, reload=True)
