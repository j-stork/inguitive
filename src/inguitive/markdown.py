"""
Markdown component for INGUITIVE framework.

Provides a component that renders Markdown content as HTML.
"""

from typing import Callable
from inguitive.components import Component


class Markdown(Component):
    """A component that renders Markdown content as HTML.
    
    Uses the Python-Markdown library to convert Markdown to HTML.
    
    Example:
        Markdown("# Hello **World**")
        Markdown(lambda: get_blog_post_content(), cls="prose")
    
    Note: This component renders raw HTML from the Markdown parser.
    If rendering untrusted user input, you should sanitize the output first.
    """
    
    def __init__(self, content: str | Callable[[], str], id: str | None = None,
                 cls: str | Callable[[], str] | None = None, **attrs):
        """Initialize a Markdown component.
        
        Args:
            content: Markdown text (string or callable returning string)
            id: Optional HTML id attribute
            cls: Optional Tailwind CSS classes (defaults to "prose" for nice typography)
            **attrs: Additional HTML attributes
        """
        # Default to Tailwind Typography for nice styling
        if cls is None:
            cls = "prose"
        super().__init__(id=id, cls=cls, **attrs)
        self.content = content

    def render(self) -> str:
        """Render the Markdown content as HTML."""
        import markdown
        resolved_content = self._resolve(self.content)
        html_content = markdown.markdown(resolved_content)
        attrs = self._get_attrs_str()
        return f"<div {attrs}>{html_content}</div>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        import markdown
        resolved_content = self._resolve(self.content)
        html_content = markdown.markdown(resolved_content)
        return f"<div {attrs}>{html_content}</div>"
