"""
Component classes for inguitive framework.
"""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from typing import Any

import jinja2
import markupsafe

from inguitive.session import _get_component_registry

# Register well-known SVG namespace prefixes with ElementTree so that round-trip
# serialisation (fromstring → tostring) preserves them instead of inventing ns0:,
# ns1:, … placeholders.  These registrations are process-global and must be set
# before any ET.tostring() call.
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
ET.register_namespace("xml", "http://www.w3.org/XML/1998/namespace")


class Component:
    """Base component class for inguitive."""

    def __init__(
        self,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        listen_to: str | list[str] | None = None,
        trigger: str | None = None,
        trigger_args: dict[str, str] | None = None,
        **attrs: Any,
    ):
        # Generate UUID if no id provided
        if id is None:
            id = f"comp-{uuid.uuid4().hex[:8]}"
        self.id = id
        self.css = css

        # Handle action parameters (trigger = POST)
        if trigger:
            url = f"/_trigger/{trigger.lstrip('/')}"
            if trigger_args:
                url += "?" + "&".join(f"{k}={v}" for k, v in trigger_args.items())
            attrs.setdefault("hx-post", url)
            attrs.setdefault("hx-target", "#hx-target")

        self.attrs = attrs
        _get_component_registry()[self.id] = self
        if listen_to:
            from inguitive.state import _get_state_by_name

            # Normalize to list for uniform handling
            state_names = [listen_to] if isinstance(listen_to, str) else listen_to
            for state_name in state_names:
                state = _get_state_by_name(state_name)
                if state is not None:
                    state.add_listener(self.id)

    def _resolve(
        self, value: str | Callable[[], str] | list | dict | tuple
    ) -> str | list | dict | tuple:
        """Resolve a potentially dynamic value (callable or static) and escape strings for HTML output."""
        resolved = value() if callable(value) else value
        if isinstance(resolved, markupsafe.Markup):
            # Already marked as safe, don't escape
            return resolved
        elif isinstance(resolved, str):
            return markupsafe.escape(resolved)
        elif isinstance(resolved, list):
            # For lists, recursively resolve each element
            return [self._resolve(item) for item in resolved]
        elif isinstance(resolved, dict):
            # For dicts, recursively resolve values
            return {k: self._resolve(v) for k, v in resolved.items()}
        elif isinstance(resolved, tuple):
            # For tuples, recursively resolve each element
            return tuple(self._resolve(item) for item in resolved)
        return resolved

    def _get_attrs_str(self) -> str:
        """Convert attributes to HTML string, handling css -> class conversion and dynamic values."""
        filtered_attrs = {}
        for k, v in self.attrs.items():
            if k != "css":
                filtered_attrs[k] = self._resolve(v)
        resolved_css = self._resolve(self.css) if self.css else None
        if resolved_css:
            filtered_attrs["class"] = resolved_css
        # Add id if present
        if self.id:
            resolved_id = self._resolve(self.id)
            filtered_attrs["id"] = (
                resolved_id
                if isinstance(resolved_id, markupsafe.Markup)
                else markupsafe.escape(str(resolved_id))
            )
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def _render_children(self) -> str:
        """Render all children of this component.

        Handles both direct child components and callable/lambda children.
        Supports nested lists of children.
        """
        children_html_parts = []
        for child in getattr(self, "children", []):
            if isinstance(child, Component):
                children_html_parts.append(child.render())
            else:
                resolved = self._resolve(child)
                if isinstance(resolved, list):
                    for item in resolved:
                        if isinstance(item, Component):
                            children_html_parts.append(item.render())
                        else:
                            children_html_parts.append(str(item))
                else:
                    if isinstance(resolved, Component):
                        children_html_parts.append(resolved.render())
                    else:
                        children_html_parts.append(str(resolved))
        return "".join(children_html_parts)

    def _oob_attrs_str(self) -> str:
        """Get attributes string with hx-swap-oob for out-of-band updates.

        Returns regular attributes if self.id is not set.
        """
        if not self.id:
            return self._get_attrs_str()
        return f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()

    @staticmethod
    def _normalize_children(children: tuple) -> list:
        """Normalize children tuple to a list.

        Supports both: Component(a, b) and Component([a, b]).

        Args:
            children: Tuple of child components/strings from *children

        Returns:
            List of children (flattened if single element was a list)
        """
        if len(children) == 1 and isinstance(children[0], list):
            return list(children[0])
        return list(children)

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    """HTML div component."""

    def __init__(
        self, *children: Any, id: str | None = None, css: str | Callable[[], str] | None = None, **attrs: Any
    ):
        super().__init__(id=id, css=css, **attrs)
        self.children = self._normalize_children(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = self._render_children()
        return f"<div {attrs}>{children_html}</div>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        children_html = self._render_children()
        return f"<div {attrs}>{children_html}</div>"


class Button(Component):
    """HTML button component with HTMX support.

    Use trigger, navigate, or redirect parameters for click actions:
    - trigger: POST action for partial updates (replaces old on_click)
    - navigate: GET navigation for full page changes
    - redirect: Immediate browser redirect
    """

    def __init__(
        self, *children: Any, id: str | None = None, css: str | Callable[[], str] | None = None, **attrs: Any
    ):
        super().__init__(id=id, css=css, **attrs)
        self.children = self._normalize_children(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = self._render_children()
        return f"<button {attrs}>{children_html}</button>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        children_html = self._render_children()
        return f"<button {attrs}>{children_html}</button>"


class Label(Component):
    """HTML label component.

    Renders a <label> element. Use for_ parameter to associate with input elements.

    Example:
        Label("Username", for_="username-input")
        Label("Remember me", for_="remember", css="text-sm")
    """

    def __init__(
        self,
        text: str | Callable[[], str],
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        for_: str | None = None,
        **attrs: Any,
    ):
        """Initialize a Label component.

        Args:
            text: Label text content
            id: HTML id attribute
            css: Tailwind CSS classes
            for_: ID of the form element this label is for (uses 'for' HTML attribute)
            **attrs: Additional HTML attributes
        """
        if for_ is not None:
            attrs["for"] = for_
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
        attrs = self._oob_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<label {attrs}>{resolved_text}</label>"


class Link(Component):
    """HTML link/anchor component for semantic navigation.

    Renders a standard <a> tag. Use for traditional links where semantic
    HTML matters (SEO, accessibility, browser behavior).

    Supports children like Div and Button, allowing nested components.

    Example:
        Link("Home", href="/")
        Link(Text("Documentation"), href="/docs", css="text-blue-500 hover:underline")
        Link(Icon(HOME_SVG), href="/", css="w-6 h-6")
        Link(Button("Click"), href="/page1")
        Link([Text("A"), Text("B")], href="/")
    """

    def __init__(
        self,
        *children: Any,
        href: str,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        **attrs: Any,
    ):
        """Initialize a Link component.

        Args:
            *children: Link content (strings, Components, or callables)
            href: URL to link to
            id: HTML id attribute
            css: Tailwind CSS classes
            **attrs: Additional HTML attributes (target, rel, etc.)
        """
        super().__init__(id=id, css=css, **attrs)
        if href:
            self.attrs["href"] = self._safe_url(href)
        self.children = self._normalize_children(children)

    @staticmethod
    def _safe_url(url: str) -> str:
        """Return the URL if its scheme is safe, otherwise return '#'.

        Blocks javascript:, vbscript:, and data: URIs that can execute
        arbitrary code. Leading whitespace is stripped before the check
        because browsers ignore it when interpreting the scheme.
        """
        if re.match(r"(?i)^\s*(javascript|vbscript|data)\s*:", url):
            return "#"
        return url

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = self._render_children()
        return f"<a {attrs}>{children_html}</a>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        children_html = self._render_children()
        return f"<a {attrs}>{children_html}</a>"


class Text(Component):
    """HTML paragraph/text component.

    Renders a <p> tag for paragraph text content. Use for standalone text blocks,
    descriptions, and any content that isn't a form label.

    Example:
        Text("Welcome to our application")
        Text("This is a paragraph", css="text-gray-600 mt-4")
        Text(lambda: get_description(), listen_to="desc_state")
    """

    def __init__(
        self,
        text: str | Callable[[], str],
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        **attrs: Any,
    ):
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
        attrs = self._oob_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<p {attrs}>{resolved_text}</p>"


class Header(Component):
    """HTML heading component.

    Renders an <h1> through <h6> tag based on the level parameter.
    Use for page titles, section headings, and hierarchical content structure.

    Example:
        Header("Main Title", level=1)
        Header("Section Heading", level=2, css="text-blue-600")
        Header(lambda: get_title(), level=3, listen_to="title_state")
    """

    def __init__(
        self,
        text: str | Callable[[], str],
        level: int = 1,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        **attrs: Any,
    ):
        """Initialize a Header component.

        Args:
            text: Text content (string or callable returning string)
            level: Heading level (1-6), defaults to 1 for <h1>
            id: HTML id attribute
            css: Tailwind CSS classes
            **attrs: Additional HTML attributes
        """
        if not 1 <= level <= 6:
            raise ValueError("Header level must be between 1 and 6")
        super().__init__(id=id, css=css, **attrs)
        self.text = text
        self.level = level

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<h{self.level} {attrs}>{resolved_text}</h{self.level}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<h{self.level} {attrs}>{resolved_text}</h{self.level}>"


class Icon(Component):
    """SVG icon component."""

    def __init__(
        self, svg: str | Callable[[], str], css: str | Callable[[], str] | None = None, **attrs: Any
    ):
        super().__init__(css=css, **attrs)
        self.svg = svg

    @staticmethod
    def _set_svg_attrs(
        svg_content: str | markupsafe.Markup,
        attrs: dict[str, str],
    ) -> str | markupsafe.Markup:
        """Set attributes on the root element of an SVG.

        Args:
            svg_content: The SVG HTML string or Markup object
            attrs: Dictionary of attribute name -> value to set on root element

        Returns:
            Processed SVG string or Markup with attributes set
        """
        is_markup = isinstance(svg_content, markupsafe.Markup)
        svg_string = str(svg_content) if is_markup else svg_content

        try:
            root = ET.fromstring(svg_string)
            for name, value in attrs.items():
                root.set(name, value)

            result = ET.tostring(root, encoding="unicode", method="xml")

            # Remove namespace prefixes and declarations
            result = re.sub(r'\s+xmlns(:\w+)?="[^"]*"', '', result)
            result = re.sub(r'<ns\d+:', '<', result)
            result = re.sub(r'</ns\d+:', '</', result)
            result = re.sub(r'(\s)ns\d+:', r'\1', result)

        except ET.ParseError as e:
            raise ValueError(
                f"Invalid SVG XML: {e}. "
                f"The Icon component requires well-formed SVG XML. "
                f"Common issues: unquoted attributes, unclosed tags, or malformed syntax. "
                f"Please validate your SVG input."
            ) from e

        if is_markup:
            return markupsafe.Markup(result)
        return result

    @staticmethod
    def _replace_class(svg_str: str, css_value: str) -> str:
        """Replace or insert class attribute in SVG string.

        Uses xml.etree.ElementTree for robust parsing of SVG content.
        Handles edge cases like self-closing tags, irregular whitespace,
        and different quote styles. Preserves all other attributes and structure.

        Args:
            svg_str: The SVG HTML string
            css_value: The new class value (without quotes)

        Returns:
            SVG string with updated class attribute
        """
        return Icon._set_svg_attrs(svg_str, {"class": css_value})

    def render(self) -> str:
        # SVG content is always developer-supplied markup, never user input.
        # Resolve the callable if needed, then ensure it is treated as trusted
        # by wrapping in Markup so it is never HTML-escaped.
        raw_svg = self.svg() if callable(self.svg) else self.svg
        resolved_svg = (
            raw_svg if isinstance(raw_svg, markupsafe.Markup) else markupsafe.Markup(raw_svg)
        )

        # Set the id (and class) on the root <svg> so HTMX out-of-band swaps
        # emitted by update() can match this element by id. Without an id here
        # the OOB response has no target in the DOM and the swap is a no-op.
        attrs: dict[str, str] = {}
        if self.id:
            attrs["id"] = self.id
        if self.css:
            css_value = self.css() if callable(self.css) else self.css
            attrs["class"] = css_value
        if attrs:
            resolved_svg = markupsafe.Markup(self._set_svg_attrs(resolved_svg, attrs))

        return resolved_svg

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()

        result = self._set_svg_attrs(
            self.svg() if callable(self.svg) else self.svg,
            {"hx-swap-oob": "true", "id": self.id},
        )

        # Apply CSS class replacement if needed
        if self.css:
            css_value = self.css() if callable(self.css) else self.css
            result = self._replace_class(result, css_value)

        return result


class Image(Component):
    """HTML image component.

    Renders an <img> tag for displaying images. Use for logos, icons, photos,
    and any visual content.

    Example:
        Image(src="/static/logo.png", alt="Company Logo", css="h-10 w-auto")
        Image(src=lambda: get_avatar_url(), alt="User Avatar", css="rounded-full h-12 w-12")
        Image(src="/static/hero.jpg", alt="Hero", loading="lazy", width="800", height="400")
    """

    def __init__(
        self,
        src: str | Callable[[], str],
        alt: str | Callable[[], str] | None = None,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        **attrs: Any,
    ):
        """Initialize an Image component.

        Args:
            src: Image source URL (string or callable returning string)
            alt: Alternative text for accessibility (string or callable returning string)
            id: HTML id attribute
            css: Tailwind CSS classes
            **attrs: Additional HTML attributes (width, height, loading, etc.)
        """
        super().__init__(id=id, css=css, **attrs)
        self.src = src
        self.alt = alt

    def render(self) -> str:
        """Render the image element."""
        attrs = self._get_attrs_str()
        resolved_src = self._resolve(self.src)
        if self.alt:
            resolved_alt = self._resolve(self.alt)
            return f'<img src="{resolved_src}" alt="{resolved_alt}" {attrs}>'
        return f'<img src="{resolved_src}" {attrs}>'

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        resolved_src = self._resolve(self.src)
        if self.alt:
            resolved_alt = self._resolve(self.alt)
            return f'<img src="{resolved_src}" alt="{resolved_alt}" {attrs}>'
        return f'<img src="{resolved_src}" {attrs}>'


class Input(Component):
    """HTML input component for text, email, password, etc.

    Example:
        Input(id="email", type="email", placeholder="Enter email", css="border rounded p-2")
        Input(id="name", value=state, listen_to="name_state")
    """

    def __init__(
        self,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        type: str = "text",
        value: str | Callable[[], str] | None = None,
        placeholder: str = "",
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
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
            attrs["value"] = value
        if placeholder:
            attrs["placeholder"] = placeholder
        if type != "text":
            attrs["type"] = type
        # Auto-set name to id if not provided
        if "name" not in attrs and id is not None:
            attrs["name"] = id
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the input element."""
        attrs = self._get_attrs_str()
        return f"<input {attrs}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        return f"<input {attrs}>"


class Textarea(Component):
    """HTML textarea component for multi-line text input.

    Example:
        Textarea(id="bio", placeholder="Tell us about yourself", rows=5)
        Textarea(id="notes", value=content_state, listen_to="notes_state")
    """

    def __init__(
        self,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        value: str | Callable[[], str] | None = None,
        placeholder: str = "",
        rows: int = 3,
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
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
            attrs["placeholder"] = placeholder
        if rows:
            attrs["rows"] = str(rows)
        # Auto-set name to id if not provided
        if "name" not in attrs and id is not None:
            attrs["name"] = id
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
        attrs = self._oob_attrs_str()
        resolved_value = self._resolve(self.value) if self.value else ""
        return f"<textarea {attrs}>{resolved_value}</textarea>"


class Select(Component):
    """HTML select dropdown component.

    Example:
        Select(id="country", options=[("us", "USA"), ("de", "Germany")], value="us")
        Select(id="theme", options=[("light", "Light"), ("dark", "Dark")],
               value=lambda: theme_state.get(), listen_to="theme_state")
    """

    def __init__(
        self,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        options: list[tuple[str, str]] | Callable[[], list[tuple[str, str]]] | None = None,
        value: str | Callable[[], str] | None = None,
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
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
        if "name" not in attrs and id is not None:
            attrs["name"] = id
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)
        self.options = options or []
        self.value = value

    def _render_options(self) -> str:
        """Render all option elements."""
        # Get raw options for comparison (before resolving)
        raw_options = self.options() if callable(self.options) else self.options
        raw_value = self.value() if callable(self.value) else self.value
        # Get resolved options for rendering
        resolved_options = self._resolve(raw_options) if raw_options else []  # type: ignore
        option_tags = []
        # Iterate through both raw and resolved options in parallel
        for (raw_val, raw_text), (val, text) in zip(raw_options or [], resolved_options or []):  # type: ignore[str-unpack]
            # val and text are already resolved (and escaped if they were strings)
            # For attribute values, we need to ensure they're strings
            str_val = str(val) if val is not None else ""
            str_text = str(text) if text is not None else ""
            # Compare raw values to determine if selected
            selected = " selected" if raw_val == raw_value else ""
            option_tags.append(f'<option value="{str_val}"{selected}>{str_text}</option>')
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
        attrs = self._oob_attrs_str()
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

    def __init__(
        self,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        checked: bool | Callable[[], bool] = False,
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
        """Initialize a Checkbox component.

        Args:
            id: HTML id attribute
            css: Tailwind CSS classes
            checked: Checked state (boolean or callable)
            listen_to: State name to listen for changes
            **attrs: Additional HTML attributes (name, required, disabled, etc.)
        """
        # Set type to checkbox
        attrs["type"] = "checkbox"
        # Auto-set name to id if not provided
        if "name" not in attrs and id is not None:
            attrs["name"] = id
        # Store checked state
        self.checked = checked
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the checkbox input element."""
        attrs = self._get_attrs_str()
        resolved_checked = self._resolve(self.checked) if self.checked else False  # type: ignore
        if resolved_checked:
            attrs += " checked"
        return f"<input {attrs}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        resolved_checked = self._resolve(self.checked) if self.checked else False  # type: ignore
        if resolved_checked:
            attrs += " checked"
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

    def __init__(
        self,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        value: str = "",
        checked: bool | Callable[[], bool] = False,
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
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
        attrs["type"] = "radio"
        if value:
            attrs["value"] = value
        # Auto-set name to id if not provided
        if "name" not in attrs and id is not None:
            attrs["name"] = id
        # Store checked state
        self.checked = checked
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)

    def render(self) -> str:
        """Render the radio input element."""
        attrs = self._get_attrs_str()
        resolved_checked = self._resolve(self.checked) if self.checked else False  # type: ignore
        if resolved_checked:
            attrs += " checked"
        return f"<input {attrs}>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        resolved_checked = self._resolve(self.checked) if self.checked else False  # type: ignore
        if resolved_checked:
            attrs += " checked"
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

    Note: Forms with triggers automatically reset after successful submission.
    """

    def __init__(
        self,
        *children: Any,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        action: str = "",
        method: str = "post",
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
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
            attrs["action"] = action
        if method:
            attrs["method"] = method
        super().__init__(id=id, css=css, listen_to=listen_to, **attrs)
        self.children = self._normalize_children(children)

        # Auto-add form reset handler for HTMX forms
        # This clears the form after successful submission
        if self.attrs.get("hx-post") and "hx-on::after-request" not in self.attrs:
            self.attrs["hx-on::after-request"] = "if(event.detail.successful) this.reset()"

    def render(self) -> str:
        """Render the form with children."""
        attrs = self._get_attrs_str()
        children_html = self._render_children()
        return f"<form {attrs}>{children_html}</form>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        children_html = self._render_children()
        return f"<form {attrs}>{children_html}</form>"


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

    def __init__(
        self,
        template: str,
        id: str | None = None,
        css: str | Callable[[], str] | None = None,
        listen_to: str | list[str] | None = None,
        **context: Any,
    ):
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
    def from_file(
        cls,
        template_path: str,
        id: str | None = None,
        css_name: str | Callable[[], str] | None = None,
        listen_to: str | list[str] | None = None,
        **context: Any,
    ):
        """Create a TemplateComponent from a template file.

        Args:
            template_path: Path to the Jinja2 template file
            id: HTML id attribute
            css_name: Tailwind CSS classes
            listen_to: State name to listen for changes
            **context: Variables to pass to the template
        """
        with open(template_path) as f:
            template_str = f.read()
        return cls(template_str, id=id, css=css_name, listen_to=listen_to, **context)

    def render(self) -> str:
        """Render the template with context variables."""
        # Resolve all context values
        resolved_context = {}
        for key, value in self.context.items():
            resolved_context[key] = self._resolve(value) if callable(value) else value  # type: ignore

        # Add component attributes to context
        resolved_context["id"] = self.id
        if self.css:
            resolved_context["css"] = self._resolve(self.css)

        # Create Jinja2 environment and render
        env = jinja2.Environment(
            loader=jinja2.BaseLoader(), autoescape=jinja2.select_autoescape(["html", "xml"])
        )
        template = env.from_string(self.template_str)
        return template.render(**resolved_context)

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()
        attrs = self._oob_attrs_str()
        # Render template content
        env = jinja2.Environment(
            loader=jinja2.BaseLoader(), autoescape=jinja2.select_autoescape(["html", "xml"])
        )
        template = env.from_string(self.template_str)
        resolved_context = {}
        for key, value in self.context.items():
            resolved_context[key] = self._resolve(value) if callable(value) else value  # type: ignore
        resolved_context["id"] = self.id
        if self.css:
            resolved_context["css"] = self._resolve(self.css)
        content = template.render(**resolved_context)
        return f"<div {attrs}>{content}</div>"


class DataTable(Component):
    """HTML table component for rendering tabular data.

    Renders a list of dictionaries as an HTML table. Each dictionary represents
    a row, and keys represent column names. Supports optional column ordering
    and fine-grained CSS styling.

    Example:
        # Basic usage with automatic column detection
        DataTable(
            data=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ],
            css="w-full"
        )

        # With explicit column order
        DataTable(
            data=[
                {"name": "Alice", "age": 30, "city": "NYC"},
                {"name": "Bob", "age": 25, "city": "LA"}
            ],
            columns=["name", "city", "age"],
            css="w-full"
        )

        # With dynamic data from state
        DataTable(
            data=table_data_state.get,
            listen_to="table_data_state",
            columns=["id", "name", "status"]
        )

        # With dictionary-based CSS for fine-grained styling
        DataTable(
            data=data,
            css={
                "table": "w-full border-2 border-blue-500",
                "header": "px-4 py-3 bg-blue-600 text-white font-bold",
                "cell": "px-4 py-3 border border-blue-200",
                "row": "hover:bg-blue-50",
            }
        )
    """

    # Default CSS classes for sub-elements (matching original hardcoded values)
    _DEFAULT_ELEMENT_CSS = {
        "header": "px-3 py-2 bg-gray-400 border border-gray-400 text-left font-semibold uppercase tracking-wider",
        "cell": "px-3 py-2 border border-gray-300",
        "row": "odd:bg-white even:bg-gray-100 hover:bg-gray-200 transition-colors",
    }

    def __init__(
        self,
        data: list[dict] | Callable[[], list[dict]],
        columns: list[str] | Callable[[], list[str] | None] | None = None,
        id: str | None = None,
        css: str
        | Mapping[str, str | Callable[[], str]]
        | Callable[[], str | Mapping[str, str | Callable[[], str]]]
        | None = None,
        listen_to: str | list[str] | None = None,
        **attrs: Any,
    ):
        """Initialize a DataTable component.

        Args:
            data: Tabular data as list of dictionaries, or callable returning such list.
                  Each dict represents a row, keys are column names.
            columns: Optional list of column names to display, in order, or callable returning such list or None.
                    If None, columns are extracted from the first row's keys.
                    Use this to control column order or select a subset of columns.
                    Can be a callable to enable dynamic column configuration based on state.
            id: HTML id attribute
            css: CSS styling. Can be:
                - str: Applied to the root <table> element (original behavior)
                - dict: Maps element types to CSS classes:
                    - "table": Root <table> element
                    - "header": <th> elements (header cells)
                    - "row": <tr> elements (body rows)
                    - "cell": <td> elements (body cells)
                - Callable: Returns either str or dict
            listen_to: State name to listen for changes (triggers re-render)
            **attrs: Additional HTML attributes (e.g., data-testid)
        """
        # Don't pass css to parent __init__ yet - we'll handle it specially
        super().__init__(id=id, css=None, listen_to=listen_to, **attrs)
        self.data = data
        self.columns = columns
        self._raw_css = css

    def _resolve_css(self) -> tuple[str, dict[str, str]]:
        """Resolve and normalize the CSS parameter.

        Returns:
            tuple: (root_css: str, element_css: dict[str, str])
                - root_css: CSS classes for the root <table> element
                - element_css: Dictionary of CSS classes for sub-elements (header, row, cell)
        """
        css = self._raw_css

        # Handle callable
        if callable(css):
            css = css()

        # Handle None
        if css is None:
            return "", {}

        # Handle string - applies to root table element
        if isinstance(css, str):
            return css, {}

        # Handle dict - can contain 'table', 'header', 'row', 'cell' keys
        if isinstance(css, dict):
            resolved_dict = {}
            root_css = ""
            for key, value in css.items():
                if callable(value):
                    value = value()
                if value is None:
                    value = ""

                # 'table' key applies to root element
                if key == "table":
                    root_css = value
                else:
                    # Other keys apply to sub-elements
                    resolved_dict[key] = value
            return root_css, resolved_dict

        # Fallback
        return "", {}

    def _get_columns(self, resolved_data: list[dict]) -> list[str]:
        """Get the list of columns to display.

        If columns parameter was provided, use it.
        Otherwise, extract from first row's keys.
        Returns empty list if data is empty.
        """
        if self.columns is not None:
            resolved = self.columns() if callable(self.columns) else self.columns
            if resolved is not None:
                return resolved
        if resolved_data:
            return list(resolved_data[0].keys())
        return []

    def _get_value(self, row: dict, column: str) -> str:
        """Get the string value for a cell, handling None and missing keys."""
        value = row.get(column, "")
        if value is None:
            return ""
        # Escape the value for HTML output
        return markupsafe.escape(str(value))

    def _render_table(self, resolved_data: list[dict], element_css: dict[str, str]) -> str:
        """Render the HTML table structure with resolved data and CSS."""
        columns = self._get_columns(resolved_data)

        # Merge user-provided CSS with defaults
        header_css = element_css.get("header", self._DEFAULT_ELEMENT_CSS["header"])
        cell_css = element_css.get("cell", self._DEFAULT_ELEMENT_CSS["cell"])
        row_css = element_css.get("row", self._DEFAULT_ELEMENT_CSS["row"])

        # Render thead - escape column names
        header_cells = "".join(
            f'<th class="{header_css}">{markupsafe.escape(str(col))}</th>' for col in columns
        )
        thead = f"<thead><tr>{header_cells}</tr></thead>"

        # Render tbody
        if not resolved_data:
            tbody = "<tbody></tbody>"
        else:
            rows_html = []
            for row in resolved_data:
                cells = "".join(
                    f'<td class="{cell_css}">{self._get_value(row, col)}</td>' for col in columns
                )
                rows_html.append(f'<tr class="{row_css}">{cells}</tr>')
            tbody = f"<tbody>{''.join(rows_html)}</tbody>"

        return f"{thead}{tbody}"

    def _build_attrs(self, root_css: str, include_oob: bool = False) -> str:
        """Build HTML attributes string with optional OOB prefix.

        Args:
            root_css: CSS classes for the root table element
            include_oob: If True, prefix with hx-swap-oob="true"

        Returns:
            Complete attributes string for <table> element
        """
        filtered_attrs = {}
        for k, v in self.attrs.items():
            if k != "css":
                filtered_attrs[k] = self._resolve(v)

        # Add root CSS to class attribute
        if root_css:
            if "class" in filtered_attrs:
                filtered_attrs["class"] = str(filtered_attrs["class"]) + " " + root_css
            else:
                filtered_attrs["class"] = root_css

        # Add id if present
        if self.id:
            resolved_id = self._resolve(self.id)
            filtered_attrs["id"] = (
                resolved_id
                if isinstance(resolved_id, markupsafe.Markup)
                else markupsafe.escape(str(resolved_id))
            )

        attrs = " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

        if include_oob:
            attrs = f'hx-swap-oob="true" {attrs}'.strip()

        return attrs

    def render(self) -> str:
        """Render the DataTable as HTML."""
        resolved_data = self.data() if callable(self.data) else self.data
        root_css, element_css = self._resolve_css()
        attrs = self._build_attrs(root_css, include_oob=False)
        table_content = self._render_table(resolved_data, element_css)
        return f"<table {attrs}>{table_content}</table>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates."""
        if not self.id:
            return self.render()

        resolved_data = self.data() if callable(self.data) else self.data
        root_css, element_css = self._resolve_css()
        attrs = self._build_attrs(root_css, include_oob=True)
        table_content = self._render_table(resolved_data, element_css)
        return f"<table {attrs}>{table_content}</table>"
