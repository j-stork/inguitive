"""
Component classes for INGUITIVE framework.
"""

from typing import Callable
from inguitive.state import get_component_registry, get_state_registry
import markdown


class Component:
    """Base component class for INGUITIVE."""
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None, 
                 listen_to: str | None = None, **attrs):
        self.id = id
        self.cls = cls
        self.attrs = attrs
        if self.id:
            get_component_registry()[self.id] = self
        if listen_to and self.id:
            # Register this component as a listener to the state
            state_registry = get_state_registry()
            if listen_to in state_registry:
                state_registry[listen_to].add_listener(self.id)

    def _resolve(self, value: str | Callable[[], str]) -> str:
        """Resolve a potentially dynamic value (callable or static)."""
        return value() if callable(value) else value

    def _get_attrs_str(self) -> str:
        """Convert attributes to HTML string, handling cls -> class conversion and dynamic values."""
        filtered_attrs = {}
        for k, v in self.attrs.items():
            if k != 'cls':
                filtered_attrs[k] = self._resolve(v)
        resolved_cls = self._resolve(self.cls) if self.cls else None
        if resolved_cls:
            filtered_attrs['class'] = resolved_cls
        # Add id if present
        if self.id:
            filtered_attrs['id'] = self.id
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    """HTML div component."""
    
    def __init__(self, *children, id: str | None = None, cls: str | Callable[[], str] | None = None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.children = list(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"


class Button(Component):
    """HTML button component with HTMX support."""
    
    def __init__(self, *children, id: str | None = None, 
                 cls: str | Callable[[], str] | None = None, 
                 on_click: str | None = None,
                 on_click_args: dict[str, str] | None = None, **attrs):
        # Convert on_click to HTMX attributes with optional query parameters
        if on_click:
            if 'hx-post' not in attrs:
                url = f"/{on_click.lstrip('/')}"
                if on_click_args:
                    url += "?" + "&".join(f"{k}={v}" for k, v in on_click_args.items())
                attrs['hx-post'] = url
            if 'hx-target' not in attrs:
                attrs['hx-target'] = "#hx-target"
        super().__init__(id=id, cls=cls, **attrs)
        self.children = list(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<button {attrs}>{children_html}</button>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<button {attrs}>{children_html}</button>"


class Label(Component):
    """HTML label/paragraph component."""
    
    def __init__(self, text: str | Callable[[], str], id: str | None = None, 
                 cls: str | Callable[[], str] | None = None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<p {attrs}>{resolved_text}</p>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        resolved_text = self._resolve(self.text)
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        return f"<p {attrs}>{resolved_text}</p>"


class Icon(Component):
    """SVG icon component."""
    
    def __init__(self, svg: str | Callable[[], str], cls: str | Callable[[], str] | None = None, **attrs):
        super().__init__(cls=cls, **attrs)
        self.svg = svg

    @staticmethod
    def _replace_class(svg_str: str, cls_value: str) -> str:
        """Replace or insert class attribute in SVG string.
        
        Preserves all other attributes, quote style, and structure.
        
        Args:
            svg_str: The SVG HTML string
            cls_value: The new class value (without quotes)
            
        Returns:
            SVG string with updated class attribute
        """
        # Find class attribute with optional whitespace between class and =
        idx = svg_str.find('class')
        if idx != -1:
            # Move past 'class'
            idx += len('class')
            # Skip whitespace
            while idx < len(svg_str) and svg_str[idx] in ' \t':
                idx += 1
            # Check for '='
            if idx < len(svg_str) and svg_str[idx] == '=':
                idx += 1
                # Skip whitespace after '='
                while idx < len(svg_str) and svg_str[idx] in ' \t':
                    idx += 1
                # Now at the opening quote
                if idx < len(svg_str) and svg_str[idx] in ('"', "'"):
                    quote_char = svg_str[idx]
                    # Find closing quote
                    content_start = idx + 1
                    content_end = svg_str.find(quote_char, content_start)
                    if content_end != -1:
                        # Replace the content between quotes
                        return (svg_str[:content_start] +
                                cls_value +
                                svg_str[content_end:])
        # No class attribute found - insert one
        if svg_str.startswith('<svg'):
            pos = len('<svg')
            return svg_str[:pos] + f' class="{cls_value}"' + svg_str[pos:]
        return f'<svg class="{cls_value}">{svg_str}'

    def render(self) -> str:
        resolved_svg: str = self._resolve(self.svg)
        
        if self.cls:
            resolved_cls: str = self._resolve(self.cls)
            resolved_svg = self._replace_class(resolved_svg, resolved_cls)
        
        return resolved_svg


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
        # Default to GitHub Markdown CSS for nice styling
        if cls is None:
            cls = "markdown-body"
        super().__init__(id=id, cls=cls, **attrs)
        self.content = content

    def render(self) -> str:
        """Render the Markdown content as HTML."""
        resolved_content = self._resolve(self.content)
        html_content = markdown.markdown(resolved_content)
        attrs = self._get_attrs_str()
        return f"<div {attrs}>{html_content}</div>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_content = self._resolve(self.content)
        html_content = markdown.markdown(resolved_content)
        return f"<div {attrs}>{html_content}</div>"
