"""
Component classes for INGUITIVE framework.
"""

import uuid
from typing import Callable
from inguitive.state import get_component_registry, get_state_registry
import markdown


class Component:
    """Base component class for INGUITIVE."""
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None, 
                 listen_to: str | None = None, **attrs):
        # Generate UUID if no id provided
        if id is None:
            id = f"comp-{uuid.uuid4().hex[:8]}"
        self.id = id
        self.cls = cls
        self.attrs = attrs
        get_component_registry()[self.id] = self
        if listen_to:
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


class Input(Component):
    """HTML input component for text, email, password, etc.
    
    Example:
        Input(id="email", type="email", placeholder="Enter email", cls="border rounded p-2")
        Input(id="name", value=state, listen_to="name_state")
    """
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None,
                 type: str = "text", value: str | Callable[[], str] | None = None,
                 placeholder: str = "", listen_to: str | None = None, **attrs):
        """Initialize an Input component.
        
        Args:
            id: HTML id attribute
            cls: Tailwind CSS classes
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
        super().__init__(id=id, cls=cls, listen_to=listen_to, **attrs)

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
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None,
                 value: str | Callable[[], str] | None = None,
                 placeholder: str = "", rows: int = 3,
                 listen_to: str | None = None, **attrs):
        """Initialize a Textarea component.
        
        Args:
            id: HTML id attribute
            cls: Tailwind CSS classes
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
        super().__init__(id=id, cls=cls, listen_to=listen_to, **attrs)
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
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None,
                 options: list[tuple[str, str]] | Callable[[], list[tuple[str, str]]] | None = None,
                 value: str | Callable[[], str] | None = None,
                 listen_to: str | None = None, **attrs):
        """Initialize a Select component.
        
        Args:
            id: HTML id attribute
            cls: Tailwind CSS classes
            options: List of (value, display_text) tuples, or callable returning such list
            value: Selected value (string or callable)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, disabled, etc.)
        """
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        super().__init__(id=id, cls=cls, listen_to=listen_to, **attrs)
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
    
    Example:
        Checkbox(id="agree", label="I agree to terms", checked=True)
        Checkbox(id="notify", label="Email notifications", 
                 checked=lambda: notify_state.get(), listen_to="notify_state")
    """
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None,
                 label: str | Callable[[], str] = "",
                 checked: bool | Callable[[], bool] = False,
                 listen_to: str | None = None, **attrs):
        """Initialize a Checkbox component.
        
        Args:
            id: HTML id attribute
            cls: Tailwind CSS classes (applied to the wrapper div)
            label: Label text displayed next to the checkbox
            checked: Checked state (boolean or callable)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, disabled, etc.)
        """
        # Set type to checkbox
        attrs['type'] = 'checkbox'
        # Auto-set name to id if not provided
        if 'name' not in attrs and id is not None:
            attrs['name'] = id
        # Store label separately (not an HTML attribute of input)
        self.label = label
        # Store checked state
        self.checked = checked
        super().__init__(id=id, cls=cls, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the checkbox with optional label."""
        # Resolve checked state
        resolved_checked = self._resolve(self.checked) if self.checked else False
        # Get existing attrs but add checked if needed
        attrs = self._get_attrs_str()
        if resolved_checked:
            attrs += ' checked'
        
        # Resolve label
        resolved_label = self._resolve(self.label) if self.label else ""
        
        # Wrap in a div for styling and label association
        if resolved_label:
            return f'<div {self._get_wrapper_attrs()}><input {attrs}><span class="ml-2">{resolved_label}</span></div>'
        return f"<input {attrs}>"
    
    def _get_wrapper_attrs(self) -> str:
        """Get attributes for the wrapper div."""
        filtered_attrs = {}
        if self.id:
            filtered_attrs['id'] = self.id
        if self.cls:
            resolved_cls = self._resolve(self.cls) if self.cls else None
            if resolved_cls:
                filtered_attrs['class'] = resolved_cls
        # Add flex and items-center for proper checkbox+label alignment
        existing_class = filtered_attrs.get('class', '')
        filtered_attrs['class'] = f"{existing_class} flex items-baseline".strip()
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        # Build attrs with hx-swap-oob
        attrs_str = self._get_attrs_str()
        hx_attrs = f'hx-swap-oob="true" {attrs_str}'.strip()
        
        resolved_checked = self._resolve(self.checked) if self.checked else False
        if resolved_checked:
            hx_attrs += ' checked'
        
        resolved_label = self._resolve(self.label) if self.label else ""
        
        if resolved_label:
            wrapper_attrs = f'hx-swap-oob="true" {self._get_wrapper_attrs()}'
            return f'<div {wrapper_attrs}><input {hx_attrs}><span class="ml-2">{resolved_label}</span></div>'
        return f"<input {hx_attrs}>"


class Radio(Component):
    """HTML radio input group component.
    
    Renders a group of radio buttons from options. Only one can be selected.
    
    Example:
        Radio(
            id="gender",
            name="gender",
            options=[("male", "Male"), ("female", "Female"), ("other", "Other")],
            value=gender_state.get,
            listen_to="gender_state",
            cls="flex gap-4"
        )
        
    Note: This replaces the old single Radio component. For individual radio buttons,
    use Input(type="radio") or create multiple Radio groups with single options.
    """
    
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None,
                 options: list[tuple[str, str]] | Callable[[], list[tuple[str, str]]] = [],
                 value: str | Callable[[], str] | None = None,
                 name: str | None = None,
                 listen_to: str | None = None, **attrs):
        """Initialize a Radio group component.
        
        Args:
            id: HTML id attribute (for the wrapper div)
            cls: Tailwind CSS classes (applied to the wrapper div)
            options: List of (value, display_text) tuples, or callable returning such list
            value: Currently selected value (string or callable)
            name: Name attribute for all radio inputs (defaults to id if not provided)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (disabled, required, etc.)
        """
        self.options = options
        self.value = value
        # Auto-set name to id if not provided
        if name is None and id is not None:
            name = id
        if name:
            attrs['name'] = name
        super().__init__(id=id, cls=cls, listen_to=listen_to, **attrs)

    def _render_radio(self, radio_value: str, display_text: str) -> str:
        """Render a single radio button."""
        resolved_value = self._resolve(self.value) if self.value else None
        checked = ' checked' if radio_value == resolved_value else ''
        resolved_text = self._resolve(display_text) if callable(display_text) else display_text
        # Build attrs for the radio input
        input_attrs = {}
        if 'name' in self.attrs:
            input_attrs['name'] = self.attrs['name']
        input_attrs['type'] = 'radio'
        input_attrs['value'] = radio_value
        # Add any other attrs from parent (disabled, required, etc.)
        for k, v in self.attrs.items():
            if k not in ('name', 'cls', 'id'):
                input_attrs[k] = v
        # Resolve all attribute values
        resolved_attrs = {}
        for k, v in input_attrs.items():
            resolved_attrs[k] = self._resolve(v) if callable(v) else v
        attrs_str = " ".join(f'{k}="{v}"' for k, v in resolved_attrs.items())
        # Generate a unique id for each radio option
        radio_id = f"{self.id}-{radio_value}" if self.id else f"radio-{uuid.uuid4().hex[:8]}"
        return f'<div class="flex items-center"><input {attrs_str}{checked} id="{radio_id}"><label for="{radio_id}" class="ml-2">{resolved_text}</label></div>'

    def render(self) -> str:
        """Render the radio group with all options."""
        resolved_options = self._resolve(self.options) if self.options else []
        radios_html = "".join(
            self._render_radio(val, text) for val, text in resolved_options
        )
        attrs = self._get_attrs_str()
        return f"<div {attrs}>{radios_html}</div>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        resolved_options = self._resolve(self.options) if self.options else []
        radios_html = "".join(
            self._render_radio(val, text) for val, text in resolved_options
        )
        return f"<div {attrs}>{radios_html}</div>"


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
        Form(on_click="save", children=[...])  # HTMX form
    """
    
    def __init__(self, *children, id: str | None = None, cls: str | Callable[[], str] | None = None,
                 action: str = "", method: str = "post",
                 listen_to: str | None = None, **attrs):
        """Initialize a Form component.
        
        Args:
            *children: Form elements (Input, Textarea, Select, Button, etc.)
            id: HTML id attribute
            cls: Tailwind CSS classes
            action: Form action URL
            method: HTTP method (get, post, etc.)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (hx-post, hx-target, etc.)
        """
        if action:
            attrs['action'] = action
        if method:
            attrs['method'] = method
        super().__init__(id=id, cls=cls, listen_to=listen_to, **attrs)
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
