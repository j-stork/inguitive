"""
Markdown demo application using INGUITIVE framework.

Demonstrates the Markdown component for rendering markdown content as HTML.

Run with: uvicorn examples.markdown_demo:app --reload
"""

from pathlib import Path

from inguitive import Div, Markdown, create_app, page

# --- Markdown Content ---
MARKDOWN_CONTENT = """
# Welcome to INGUITIVE Markdown Demo

This demonstrates the **Markdown** component that renders markdown as HTML.

## Features

- **Bold** and *italic* text
- `code formatting`
- Lists:
  - Item 1
  - Item 2
  - Item 3

## Code Example

```python
from inguitive import Markdown

# Simple usage
Markdown("# Hello **World**")

# With custom styling
Markdown(content, css="prose prose-lg dark:prose-invert")
```

## Tables

| Feature | Status |
|---------|--------|
| Easy to use | ✅ |
| Fast | ✅ |
| Flexible | ✅ |

## Links

Visit [INGUITIVE on GitHub](https://github.com) for more information.

---

> **Note:** This component uses Python-Markdown under the hood and defaults to
> Tailwind Typography's `prose` class for beautiful typography.
"""


# --- Demo Component ---
def MarkdownDemo() -> Div:
    """Demo component showing Markdown rendering."""
    return Div(
        Markdown(MARKDOWN_CONTENT, id="markdown-content"),
        css="w-full max-w-4xl mx-auto p-6"
    )


# --- Routes ---
@page("/")
def home():
    return MarkdownDemo()


# --- App Setup ---
app, templates = create_app(template_dir=Path(__file__).parent / "templates")


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("examples.markdown_demo:app", host="0.0.0.0", port=8000, reload=True)
