"""
Component classes for INGUITIVE framework.
"""

from __future__ import annotations

import uuid
from typing import Callable
from inguitive.session import get_component_registry
import markdown
import jinja2


class Component:
    """Base component class for INGUITIVE."""
    
    def __init__(self, id: str | None = None, css: str | Callable[[], str] | None = None, 
                 listen_to: str | None = None, 
                 trigger: str | None = None,
                 trigger_args: dict[str, str] | None = None,
                 navigate: str | None = None,
                 redirect: str | None = None,
                 **attrs):
        # Generate UUID if no id provided
        if id is None:
            id = f"comp-{uuid.uuid4().hex[:8]}"
        self.id = id
        self.css = css
        
        # Handle action parameters (trigger = POST, navigate = GET, redirect = redirect)
        if trigger:
            url = f"/{trigger.lstrip('/')}"
            if trigger_args:
                url += "?" + "&".join(f"{k}={v}" for k, v in trigger_args.items())
            attrs.setdefault('hx-post', url)
            attrs.setdefault('hx-target', "#hx-target")
        if navigate:
            attrs.setdefault('hx-get', f"/{navigate.lstrip('/')}")
            attrs.setdefault('hx-target', "body")
        if redirect:
            attrs.setdefault('hx-redirect', f"{redirect.lstrip('/')}")

        
        self.attrs = attrs
        get_component_registry()[self.id] = self
        if listen_to:
            from inguitive.state import get_state_by_name
            state = get_state_by_name(listen_to)
            if state is not None:
                state.add_listener(self.id)

    def _resolve(self, value: str | Callable[[], str]) -> str:
        """Resolve a potentially dynamic value (callable or static)."""
        return value() if callable(value) else value

    def _get_attrs_str(self) -> str:
        """Convert attributes to HTML string, handling css -> class conversion and dynamic values."""
        filtered_attrs = {}
        for k, v in self.attrs.items():
            if k != 'css':
                filtered_attrs[k] = self._resolve(v)
        resolved_css = self._resolve(self.css) if self.css else None
        if resolved_css:
            filtered_attrs['class'] = resolved_css
        # Add id if present
        if self.id:
            filtered_attrs['id'] = self.id
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    """HTML div component."""
    
    def __init__(self, *children, id: str | None = None, css: str | Callable[[], str] | None = None, **attrs):
        super().__init__(id=id, css=css, **attrs)
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
    """HTML button component with HTMX support.
    
    Use trigger, navigate, or redirect parameters for click actions:
    - trigger: POST action for partial updates (replaces old on_click)
    - navigate: GET navigation for full page changes
    - redirect: Immediate browser redirect
    """
    
    def __init__(self, *children, id: str | None = None, 
                 css: str | Callable[[], str] | None = None, 
                 **attrs):
        super().__init__(id=id, css=css, **attrs)
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
    """HTML label component.
    
    Renders a <label> element. Use for_ parameter to associate with input elements.
    
    Example:
        Label("Username", for_="username-input")
        Label("Remember me", for_="remember", css="text-sm")
    """
    
    def __init__(self, text: str | Callable[[], str], id: str | None = None, 
                 css: str | Callable[[], str] | None = None, 
                 for_: str | None = None, **attrs):
        """Initialize a Label component.
        
        Args:
            text: Label text content
            id: HTML id attribute
            css: Tailwind CSS classes
            for_: ID of the form element this label is for (uses 'for' HTML attribute)
            **attrs: Additional HTML attributes
        """
        if for_ is not None:
            attrs['for'] = for_
        super().__init__(id=id, css=css, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<label {attrs}>{resolved_text}</label>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_text = self._resolve(self.text)
        return f"<label {attrs}>{resolved_text}</label>"


class Link(Component):
    """HTML link/anchor component for semantic navigation.
    
    Renders a standard <a> tag. Use for traditional links where semantic
    HTML matters (SEO, accessibility, browser behavior).
    
    Example:
        Link("Home", href="/")
        Link("Documentation", href="/docs", css="text-blue-500 hover:underline")
        Link(Icon(HOME_SVG), href="/", css="w-6 h-6")
    """
    
    def __init__(self, text: str | Callable[[], str], href: str,
                 id: str | None = None, css: str | Callable[[], str] | None = None,
                 **attrs):
        """Initialize a Link component.
        
        Args:
            text: Link text content (string or callable returning string)
            href: URL to link to
            id: HTML id attribute
            css: Tailwind CSS classes
            **attrs: Additional HTML attributes (target, rel, etc.)
        """
        super().__init__(id=id, css=css, **attrs)
        if href:
            attrs['href'] = href
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<a {attrs}>{resolved_text}</a>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_text = self._resolve(self.text)
        return f"<a {attrs}>{resolved_text}</a>"


class Text(Component):
    """HTML paragraph/text component.
    
    Renders a <p> tag for paragraph text content. Use for standalone text blocks,
    descriptions, and any content that isn't a form label.
    
    Example:
        Text("Welcome to our application")
        Text("This is a paragraph", css="text-gray-600 mt-4")
        Text(lambda: get_description(), listen_to="desc_state")
    """
    
    def __init__(self, text: str | Callable[[], str], id: str | None = None,
                 css: str | Callable[[], str] | None = None, **attrs):
        """Initialize a Text component.
        
        Args:
            text: Text content (string or callable returning string)
            id: HTML id attribute
            css: Tailwind CSS classes
            **attrs: Additional HTML attributes
        """
        super().__init__(id=id, css=css, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<p {attrs}>{resolved_text}</p>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_text = self._resolve(self.text)
        return f"<p {attrs}>{resolved_text}</p>"


class Icon(Component):
    """SVG icon component."""
    
    def __init__(self, svg: str | Callable[[], str], css: str | Callable[[], str] | None = None, **attrs):
        super().__init__(css=css, **attrs)
        self.svg = svg

    @staticmethod
    def _replace_class(svg_str: str, css_value: str) -> str:
        """Replace or insert class attribute in SVG string.
        
        Preserves all other attributes, quote style, and structure.
        
        Args:
            svg_str: The SVG HTML string
            css_value: The new class value (without quotes)
            
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
                                css_value +
                                svg_str[content_end:])
        # No class attribute found - insert one
        if svg_str.startswith('<svg'):
            pos = len('<svg')
            return svg_str[:pos] + f' class="{css_value}"' + svg_str[pos:]
        return f'<svg class="{css_value}">{svg_str}'

    def render(self) -> str:
        resolved_svg: str = self._resolve(self.svg)
        
        if self.css:
            resolved_css: str = self._resolve(self.css)
            resolved_svg = self._replace_class(resolved_svg, resolved_css)
        
        return resolved_svg


class Input(Component):
    """HTML input component for text, email, password, etc.
    
    Example:
        Input(id="email", type="email", placeholder="Enter email", css="border rounded p-2")
        Input(id="name", value=state, listen_to="name_state")
    """
    
    def __init__(self, id: str | None = None, css: str | Callable[[], str] | None = None,
                 type: str = "text", value: str | Callable[[], str] | None = None,
                 placeholder: str = "", listen_to: str | None = None, **attrs):
        """Initialize an Input component.
        
        Args:
            id: HTML id attribute
            css: Tailwind CSS classes
            type: Input type (text, email, password, number, etc.)
            value: Initial value (string or callable)
            placeholder: Placeholder text
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, etc.)
        """
        # Set default value
        if value is not None:
            attrs['value'] = value
        if placeholder:
            attrs['placeholder'] = placeholder
        if type != "text":
            attrs['type'] = type
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the input element."""
        attrs = self._get_attrs_str()
        return f"<input {attrs}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        return f"<input {attrs}>"


class Textarea(Component):
    """HTML textarea component for multi-line text input.
    
    Example:
        Textarea(id="bio", placeholder="Tell us about yourself", rows=5)
        Textarea(id="notes", value=content_state, listen_to="notes_state")
    """
    
    def __init__(self, id: str | None = None, css: str | Callable[[], str] | None = None,
                 value: str | Callable[[], str] | None = None,
                 placeholder: str = "", rows: int = 3,
                 listen_to: str | None = None, **attrs):
        """Initialize a Textarea component.
        
        Args:
            id: HTML id attribute
            css: Tailwind CSS classes
            value: Initial value (string or callable)
            placeholder: Placeholder text
            rows: Number of visible rows
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, etc.)
        """
        if placeholder:
            attrs['placeholder'] = placeholder
        if rows:
            attrs['rows'] = str(rows)
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)
        self.value = value

    def render(self) -> str:
        """Render the textarea element."""
        attrs = self._get_attrs_str()
        # Textarea content goes between tags, not in value attribute
        resolved_value = self._resolve(self.value) if self.value else ""
        return f"<textarea {attrs}>{resolved_value}</textarea>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_value = self._resolve(self.value) if self.value else ""
        return f"<textarea {attrs}>{resolved_value}</textarea>"


class Select(Component):
    """HTML select dropdown component.
    
    Example:
        Select(id="country", options=[("us", "USA"), ("de", "Germany")], value="us")
        Select(id="theme", options=[("light", "Light"), ("dark", "Dark")], 
               value=lambda: theme_state.get(), listen_to="theme_state")
    """
    
    def __init__(self, id: str | None = None, css: str | Callable[[], str] | None = None,
                 options: list[tuple[str, str]] | Callable[[], list[tuple[str, str]]] | None = None,
                 value: str | Callable[[], str] | None = None,
                 listen_to: str | None = None, **attrs):
        """Initialize a Select component.
        
        Args:
            id: HTML id attribute
            css: Tailwind CSS classes
            options: List of (value, display_text) tuples, or callable returning such list
            value: Selected value (string or callable)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, disabled, etc.)
        """
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)
        self.options = options or []
        self.value = value

    def _render_options(self) -> str:
        """Render all option elements."""
        resolved_options = self._resolve(self.options) if self.options else []
        resolved_value = self._resolve(self.value) if self.value else None
        option_tags = []
        for val, text in resolved_options:
            selected = ' selected' if val == resolved_value else ''
            option_tags.append(f'<option value="{val}"{selected}>{text}</option>')
        return "".join(option_tags)

    def render(self) -> str:
        """Render the select element with options."""
        attrs = self._get_attrs_str()
        options_html = self._render_options()
        return f"<select {attrs}>{options_html}</select>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        options_html = self._render_options()
        return f"<select {attrs}>{options_html}</select>"


class Checkbox(Component):
    """HTML checkbox input component.
    
    Renders only the <input type="checkbox"> element. Use with Label and Div
    for composed structures.
    
    Example:
        Div(
            Checkbox(id="agree", checked=True),
            Label("I agree to terms", for_="agree"),
            css="flex items-center gap-2"
        )
    """
    
    def __init__(self, id: str | None = None, css: str | Callable[[], str] | None = None,
                 checked: bool | Callable[[], bool] = False,
                 listen_to: str | None = None, **attrs):
        """Initialize a Checkbox component.
        
        Args:
            id: HTML id attribute
            css: Tailwind CSS classes
            checked: Checked state (boolean or callable)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, disabled, etc.)
        """
        # Set type to checkbox
        attrs['type'] = 'checkbox'
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        # Store checked state
        self.checked = checked
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the checkbox input element."""
        attrs = self._get_attrs_str()
        resolved_checked = self._resolve(self.checked) if self.checked else False
        if resolved_checked:
            attrs += ' checked'
        return f"<input {attrs}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_checked = self._resolve(self.checked) if self.checked else False
        if resolved_checked:
            attrs += ' checked'
        return f"<input {attrs}>"


class Radio(Component):
    """HTML radio input component.
    
    Renders only the <input type="radio"> element. Use with Label and Div
    for composed radio groups.
    
    Example:
        Div(
            Radio(id="male", name="gender", value="male", checked=True),
            Label("Male", for_="male"),
            Radio(id="female", name="gender", value="female"),
            Label("Female", for_="female"),
            css="flex gap-4"
        )
    """
    
    def __init__(self, id: str | None = None, css: str | Callable[[], str] | None = None,
                 value: str = "",
                 checked: bool | Callable[[], bool] = False,
                 listen_to: str | None = None, **attrs):
        """Initialize a Radio component.
        
        Args:
            id: HTML id attribute
            css: Tailwind CSS classes
            value: Value for this radio option
            checked: Checked state (boolean or callable)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, disabled, etc.)
        """
        # Set type to radio
        attrs['type'] = 'radio'
        if value:
            attrs['value'] = value
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        # Store checked state
        self.checked = checked
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the radio input element."""
        attrs = self._get_attrs_str()
        resolved_checked = self._resolve(self.checked) if self.checked else False
        if resolved_checked:
            attrs += ' checked'
        return f"<input {attrs}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_checked = self._resolve(self.checked) if self.checked else False
        if resolved_checked:
            attrs += ' checked'
        return f"<input {attrs}>"


class Form(Component):
    """HTML form component for grouping input elements.
    
    Example:
        Form(
            Input(id="name", name="name"),
            Select(id="country", name="country", options=[...]),
            Button("Submit", type="submit"),
            action="/submit",
            method="POST"
        )
        Form(Button("Save", trigger="save"), ...)  # HTMX form with trigger
    """
    
    def __init__(self, *children, id: str | None = None, css: str | Callable[[], str] | None = None,
                 action: str = "", method: str = "post",
                 listen_to: str | None = None, **attrs):
        """Initialize a Form component.
        
        Args:
            *children: Form elements (Input, Textarea, Select, Button, etc.)
            id: HTML id attribute
            css: Tailwind CSS classes
            action: Form action URL
            method: HTTP method (get, post, etc.)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (hx-post, hx-target, etc.)
        """
        if action:
            attrs['action'] = action
        if method:
            attrs['method'] = method
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)
        self.children = list(children)

    def render(self) -> str:
        """Render the form with children."""
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<form {attrs}>{children_html}</form>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<form {attrs}>{children_html}</form>"


class Markdown(Component):
    """A component that renders Markdown content as HTML.
    
    Uses the Python-Markdown library to convert Markdown to HTML.
    
    Example:
        Markdown("# Hello **World**")
        Markdown(lambda: get_blog_post_content(), css="prose")
    
    Note: This component renders raw HTML from the Markdown parser.
    If rendering untrusted user input, you should sanitize the output first.
    """
    
    def __init__(self, content: str | Callable[[], str], id: str | None = None,
                 css: str | Callable[[], str] | None = None, **attrs):
        """Initialize a Markdown component.
        
        Args:
            content: Markdown text (string or callable returning string)
            id: Optional HTML id attribute
            css: Optional Tailwind CSS classes (defaults to "prose" for nice typography)
            **attrs: Additional HTML attributes
        """
        # Default to GitHub Markdown CSS for nice styling
        if css is None:
            css = "markdown-body"
        super().__init__(id=id, css=css, **attrs)
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


class TemplateComponent(Component):
    """Component that renders a Jinja2 template.
    
    Allows embedding complex HTML structures with dynamic content using Jinja2 templating.
    
    Example:
        # Inline template
        TemplateComponent(
            template='<div class="{{ css }}">{{ content }}</div>',
            content="Hello World",
            css="text-red-500"
        )
        
        # Template with state
        TemplateComponent(
            template='<span>{{ value }}</span>',
            value=my_state.get,
            listen_to="my_state"
        )
    """
    
    def __init__(self, template: str, id: str | None = None,
                 css: str | Callable[[], str] | None = None,
                 listen_to: str | None = None, **context):
        """Initialize a TemplateComponent.
        
        Args:
            template: Jinja2 template string with placeholders
            id: HTML id attribute
            css: Tailwind CSS classes
            listen_to: State name to listen for changes
            **context: Variables to pass to the template
        """
        super().__init__(id=id, css=css, listen_to=listen_to)
        self.template_str = template
        self.context = context

    @classmethod
    def from_file(cls, template_path: str, id: str | None = None,
                  css_name: str | Callable[[], str] | None = None,
                  listen_to: str | None = None, **context):
        """Create a TemplateComponent from a template file.
        
        Args:
            template_path: Path to the Jinja2 template file
            id: HTML id attribute
            css_name: Tailwind CSS classes
            listen_to: State name to listen for changes
            **context: Variables to pass to the template
        """
        with open(template_path, 'r') as f:
            template_str = f.read()
        return cls(template_str, id=id, css=css_name, listen_to=listen_to, **context)

    def render(self) -> str:
        """Render the template with context variables."""
        # Resolve all context values
        resolved_context = {}
        for key, value in self.context.items():
            resolved_context[key] = self._resolve(value) if callable(value) else value
        
        # Add component attributes to context
        resolved_context['id'] = self.id
        if self.css:
            resolved_context['css'] = self._resolve(self.css)
        
        # Create Jinja2 environment and render
        env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        template = env.from_string(self.template_str)
        return template.render(**resolved_context)

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true"'
        if self.id:
            attrs += f' id="{self.id}"'
        if self.css:
            resolved_css = self._resolve(self.css)
            attrs += f' class="{resolved_css}"'
        # Render template content
        env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        template = env.from_string(self.template_str)
        resolved_context = {}
        for key, value in self.context.items():
            resolved_context[key] = self._resolve(value) if callable(value) else value
        resolved_context['id'] = self.id
        if self.css:
            resolved_context['css'] = self._resolve(self.css)
        content = template.render(**resolved_context)
        return f"<div {attrs}>{content}</div>"
