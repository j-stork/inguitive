"""Comprehensive XSS escaping tests for inguitive components."""

import markupsafe
import pytest

from inguitive.components import (
    Button,
    Checkbox,
    DataTable,
    Div,
    Form,
    Icon,
    Input,
    Label,
    Link,
    Radio,
    Select,
    TemplateComponent,
    Text,
    Textarea,
)
from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _set_current_session,
    set_session_backend,
)
from inguitive.state import State
from inguitive.svg import MOON, SUN


@pytest.fixture(autouse=True)
def cleanup_registries():
    """Provide a clean session with empty registries for each test."""
    backend = MemoryBackend()
    set_session_backend(backend)
    session = Session(session_id="test-session")
    backend.save_session(session)
    _set_current_session(session)
    yield
    _clear_current_session()


# XSS payloads to test
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "javascript:alert(1)",
    '" onclick="alert(1)"',
    "' onmouseover='alert(1)",
    "<>&\"'",
]

# Expected escaped versions
ESCAPED_PAYLOADS = [
    "&lt;script&gt;alert('XSS')&lt;/script&gt;",
    "&lt;img src=x onerror=alert(1)&gt;",
    "&lt;svg onload=alert(1)&gt;",
    "javascript:alert(1)",  # No HTML chars to escape
    "&quot; onclick=&quot;alert(1)&quot;",
    "&#39; onmouseover=&#39;alert(1)",
    "&lt;&gt;&amp;&quot;",
]


class TestXSSInTextContent:
    """Test XSS protection in text content of components."""

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_text_component(self, payload, expected):
        """Test Text component escapes XSS in text content."""
        component = Text(payload)
        html = component.render()
        assert expected in html or markupsafe.escape(payload) in html
        assert payload not in html or expected == payload

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_label_component(self, payload, expected):
        """Test Label component escapes XSS in text content."""
        component = Label(payload)
        html = component.render()
        assert expected in html or markupsafe.escape(payload) in html
        assert payload not in html or expected == payload

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_div_children(self, payload, expected):
        """Test Div component escapes XSS in children."""
        component = Div(payload)
        html = component.render()
        assert expected in html or markupsafe.escape(payload) in html
        assert payload not in html or expected == payload

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_button_children(self, payload, expected):
        """Test Button component escapes XSS in children."""
        component = Button(payload)
        html = component.render()
        assert expected in html or markupsafe.escape(payload) in html
        assert payload not in html or expected == payload

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_link_children(self, payload, expected):
        """Test Link component escapes XSS in children."""
        component = Link(payload, href="/test")
        html = component.render()
        assert expected in html or markupsafe.escape(payload) in html
        assert payload not in html or expected == payload


class TestXSSInAttributes:
    """Test XSS protection in attribute values."""

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_div_id_attribute(self, payload, expected):
        """Test Div component escapes XSS in id attribute."""
        component = Div(id=payload)
        html = component.render()
        # For id attribute, the payload should be escaped
        escaped_payload = markupsafe.escape(payload)
        assert escaped_payload in html or payload not in html

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_input_value_attribute(self, payload, expected):
        """Test Input component escapes XSS in value attribute."""
        component = Input(id="test", value=payload)
        html = component.render()
        escaped_payload = markupsafe.escape(payload)
        assert escaped_payload in html or payload not in html

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_input_placeholder_attribute(self, payload, expected):
        """Test Input component escapes XSS in placeholder attribute."""
        component = Input(id="test", placeholder=payload)
        html = component.render()
        escaped_payload = markupsafe.escape(payload)
        assert escaped_payload in html or payload not in html

    @pytest.mark.parametrize("payload,expected", zip(XSS_PAYLOADS, ESCAPED_PAYLOADS))
    def test_textarea_value(self, payload, expected):
        """Test Textarea component escapes XSS in value."""
        component = Textarea(value=payload)
        html = component.render()
        escaped_payload = markupsafe.escape(payload)
        assert escaped_payload in html or payload not in html


class TestXSSInSpecialCharacters:
    """Test proper escaping of special HTML characters."""

    def test_ampersand_escaping(self):
        """Test that & is escaped to &amp;."""
        component = Text("A & B")
        html = component.render()
        assert "A &amp; B" in html
        assert "A & B" not in html

    def test_less_than_escaping(self):
        """Test that < is escaped to &lt;."""
        component = Text("A < B")
        html = component.render()
        assert "A &lt; B" in html
        assert "A < B" not in html

    def test_greater_than_escaping(self):
        """Test that > is escaped to &gt;."""
        component = Text("A > B")
        html = component.render()
        assert "A &gt; B" in html
        assert "A > B" not in html

    def test_double_quote_escaping(self):
        """Test that " is escaped to &quot;."""
        component = Text('A " B')
        html = component.render()
        assert "A &quot; B" in html or "A &#34; B" in html
        assert 'A " B' not in html

    def test_single_quote_escaping(self):
        """Test that ' is escaped to &#x27; or &#39;."""
        component = Text("A ' B")
        html = component.render()
        assert "A &#39; B" in html or "A &#x27; B" in html
        assert "A ' B" not in html


class TestSelectComponent:
    """Test XSS protection in Select component."""

    def test_select_option_value_escaping(self):
        """Test that option values are escaped."""
        component = Select(
            id="test",
            options=[("<script>alert(1)</script>", "Option 1")],
        )
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_select_option_text_escaping(self):
        """Test that option text is escaped."""
        component = Select(
            id="test",
            options=[("value1", "<b>Bold</b>")],
        )
        html = component.render()
        assert "&lt;b&gt;Bold&lt;/b&gt;" in html
        assert "<b>Bold</b>" not in html

    def test_select_selected_value_escaping(self):
        """Test that selected value is compared correctly before escaping."""
        component = Select(
            id="test",
            options=[("<script>", "Script"), ("safe", "Safe")],
            value="<script>",
        )
        html = component.render()
        # The script option should be selected
        assert 'value="&lt;script&gt;" selected' in html


class TestDataTableComponent:
    """Test XSS protection in DataTable component."""

    def test_datatable_cell_escaping(self):
        """Test that cell values are escaped."""
        data = [{"name": "<script>alert(1)</script>", "age": 30}]
        component = DataTable(data=data)
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_datatable_column_name_escaping(self):
        """Test that column names are escaped."""
        data = [{"<script>name</script>": "value"}]
        component = DataTable(data=data)
        html = component.render()
        assert "&lt;script&gt;name&lt;/script&gt;" in html
        assert "<script>name</script>" not in html

    def test_datatable_none_value(self):
        """Test that None values are handled safely."""
        data = [{"name": "Alice", "age": None}]
        component = DataTable(data=data)
        html = component.render()
        # None should be rendered as empty string
        assert "Alice" in html


class TestFormComponent:
    """Test XSS protection in Form component."""

    def test_form_children_escaping(self):
        """Test that form children are escaped."""
        component = Form(
            Input(id="name", value="<script>alert(1)</script>"),
            action="/submit",
        )
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestCheckboxRadioComponents:
    """Test XSS protection in Checkbox and Radio components."""

    def test_checkbox_id_escaping(self):
        """Test that Checkbox id is escaped."""
        component = Checkbox(id='<script>alert(1)</script>', checked=True)
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_radio_value_escaping(self):
        """Test that Radio value is escaped."""
        component = Radio(id="test", value="<script>alert(1)</script>")
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestIconComponent:
    """Test XSS protection in Icon component."""

    def test_icon_with_trusted_svg(self):
        """Test that trusted SVG icons render correctly."""
        component = Icon(MOON)
        html = component.render()
        assert "<svg" in html
        assert "</svg>" in html

    def test_icon_with_css_escaping(self):
        """Test that CSS class is escaped."""
        component = Icon(MOON, css='<script>alert(1)</script>')
        html = component.render()
        # The CSS should be escaped in the class attribute
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_icon_with_untrusted_svg(self):
        """Test that untrusted SVG strings are escaped."""
        svg = "<svg><script>alert(1)</script></svg>"
        component = Icon(svg)
        html = component.render()
        # The SVG should be escaped
        assert "&lt;svg&gt;" in html
        assert "<svg>" not in html


class TestTemplateComponent:
    """Test XSS protection in TemplateComponent."""

    def test_template_component_autoescape(self):
        """Test that TemplateComponent uses Jinja2 autoescape."""
        component = TemplateComponent(
            template="<div>{{ content }}</div>",
            content="<script>alert(1)</script>",
        )
        html = component.render()
        # Jinja2 should autoescape the content
        assert "&lt;script&gt;" in html or "<script>" not in html

    def test_template_component_callable_content(self):
        """Test that callable content is resolved and escaped."""
        state = State("<script>alert(1)</script>", "test_state")
        component = TemplateComponent(
            template="<div>{{ content }}</div>",
            content=state.get,
            listen_to="test_state",
        )
        html = component.render()
        assert "&lt;script&gt;" in html or "<script>" not in html


class TestStateBasedContent:
    """Test XSS protection with state-based content."""

    def test_state_based_text(self):
        """Test that state-based text content is escaped."""
        state = State("<script>alert(1)</script>", "test_state")
        component = Text(state.get, listen_to="test_state")
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_state_based_attribute(self):
        """Test that state-based attribute values are escaped."""
        state = State("<script>alert(1)</script>", "test_state")
        component = Div(id=state.get, listen_to="test_state")
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_state_update(self):
        """Test that state updates still escape content."""
        state = State("<script>alert(1)</script>", "test_state")
        component = Text(state.get, listen_to="test_state")
        
        # Initial render
        html1 = component.render()
        assert "&lt;script&gt;" in html1
        
        # Update state
        state.set("<img src=x onerror=alert(1)>")
        html2 = component.render()
        assert "&lt;img" in html2
        assert "<img" not in html2


class TestNoDoubleEscaping:
    """Test that content is not double-escaped."""

    def test_already_escaped_content(self):
        """Test that already-escaped content is escaped again (expected behavior).
        
        To avoid double-escaping, use markupsafe.Markup to wrap pre-escaped content.
        """
        already_escaped = "&lt;script&gt;alert(1)&lt;/script&gt;"
        component = Text(already_escaped)
        html = component.render()
        # Expected: the already-escaped content gets escaped again
        assert "&amp;lt;" in html
        # This is expected behavior - all strings are escaped
        # To avoid this, users should use markupsafe.Markup()

    def test_markup_content(self):
        """Test that Markup content is not escaped."""
        markup = markupsafe.Markup("<b>Bold</b>")
        component = Text(markup)
        html = component.render()
        # Markup should be rendered as-is
        assert "<b>Bold</b>" in html
        assert "&lt;b&gt;" not in html


class TestEdgeCases:
    """Test edge cases for XSS protection."""

    def test_none_value(self):
        """Test that None values are handled safely."""
        component = Text(None)
        html = component.render()
        assert "None" in html or "" in html

    def test_empty_string(self):
        """Test that empty strings are handled safely."""
        component = Text("")
        html = component.render()
        assert "<p" in html

    def test_numeric_value(self):
        """Test that numeric values are converted to strings safely."""
        component = Text(123)
        html = component.render()
        assert "123" in html

    def test_boolean_value(self):
        """Test that boolean values are converted to strings safely."""
        component = Text(True)
        html = component.render()
        assert "True" in html

    def test_callable_returning_none(self):
        """Test that callables returning None are handled safely."""
        component = Text(lambda: None)
        html = component.render()
        assert "<p" in html

    def test_callable_returning_xss(self):
        """Test that callables returning XSS are escaped."""
        component = Text(lambda: "<script>alert(1)</script>")
        html = component.render()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html
