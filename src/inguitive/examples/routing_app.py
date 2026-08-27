"""
Multi-page routing example using inguitive.

Run with: uvicorn inguitive.examples.routing_app:app --reload

Routing: @app.page, redirect, and Link
--------------------------------------
This example demonstrates three pieces of inguitive's routing layer:

1. **Multiple pages via ``@app.page``.** Each ``@app.page("/path")``
   decorator registers a GET route that returns a full page component. Here
   ``/home`` and ``/about`` are two distinct pages with their own URLs.

2. **``redirect`` for URL-level navigation.** The root path ``/`` returns
   ``redirect("/home")``, which issues an HTTP 302 so the browser's address
   bar updates to the target URL. This is the "URL changes" model — a real
   page transition, not an in-place content swap.

3. **``Link`` for anchor navigation.** ``Link`` renders an ``<a>`` tag whose
   ``href`` points at another route. Clicking it triggers a normal browser
   navigation, so the URL changes and the matching ``@app.page`` handler
   renders. Links can wrap other components (here, a styled ``Button``).

Contrast with ``counter_app.py`` and the trigger-handler apps, where
interactions stay on a single page and update content via HTMX OOB swaps
without a URL change.

To test:
1. Visit ``/`` — the browser redirects to ``/home`` (address bar updates)
2. Click "Go to About" — the URL changes to ``/about``
3. Click "Back to Home" — the URL changes back to ``/home``
"""

from inguitive import Button, Div, Link, Text, create_app, redirect

from .css import BUTTON_PRIMARY_CSS

# --- App Setup ---
app = create_app()


# --- Shared Components ---
def PageCard(title: str, *content) -> Div:  # noqa: N802
    """A simple page shell with a heading and the given content."""
    return Div(
        Text(title, css="text-2xl font-bold text-slate-900"),
        *content,
        css="max-w-md mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg space-y-6",
    )


def NavButton(label: str, href: str) -> Link:  # noqa: N802
    """A Link wrapping a styled Button — clicking navigates to ``href``."""
    return Link(
        Button(label, css=f"{BUTTON_PRIMARY_CSS} w-full"),
        href=href,
        css="block",
    )


# --- Routes ---
@app.page("/")
def root():
    """Redirect the bare root path to /home."""
    return redirect("/home")


@app.page("/home")
def home():
    return PageCard(
        "Home",
        Text("This is the home page. The URL is /home.", css="text-slate-600"),
        NavButton("Go to About", href="/about"),
    )


@app.page("/about")
def about():
    return PageCard(
        "About",
        Text("This is the about page. The URL is /about.", css="text-slate-600"),
        NavButton("Back to Home", href="/home"),
    )


# --- Start ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inguitive.examples.routing_app:app", host="0.0.0.0", port=8000, reload=True)
