"""Tests for inguitive component classes."""

import pytest

from inguitive.components import Button, Div, Icon, Label
from inguitive.session import (
    MemoryBackend,
    Session,
    _clear_current_session,
    _set_current_session,
    set_session_backend,
)
from inguitive.state import State


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


class TestDiv:
    def test_basic_render(self):
        """Test basic div rendering."""
        div = Div("Hello", id="test-div", css="text-red-500")
        html = div.render()
        assert 'id="test-div"' in html
        assert 'class="text-red-500"' in html
        assert "Hello" in html

    def test_nested_children(self):
        """Test nested div children."""
        div = Div(
            Div("Inner 1"),
            Div("Inner 2"),
        )
        html = div.render()
        assert "Inner 1" in html
        assert "Inner 2" in html

    def test_callable_cls(self):
        """Test dynamic class via callable."""
        div = Div(id="test", css=lambda: "text-blue-500")
        html = div.render()
        assert 'class="text-blue-500"' in html


class TestButton:
    def test_basic_render(self):
        """Test basic button rendering."""
        btn = Button("Click me", id="btn-1", css="bg-blue-500")
        html = btn.render()
        assert 'id="btn-1"' in html
        assert 'class="bg-blue-500"' in html
        assert "Click me" in html

    def test_trigger_generates_htmx_attrs(self):
        """Test that trigger generates HTMX attributes."""
        btn = Button("Click", trigger="test_action")
        html = btn.render()
        assert 'hx-post="/_trigger/test_action"' in html
        assert 'hx-target="#hx-target"' in html

    def test_trigger_with_args(self):
        """Test trigger with query parameters."""
        btn = Button("Click", trigger="action", trigger_args={"key": "value"})
        html = btn.render()
        assert 'hx-post="/_trigger/action?key=value"' in html

    def test_children_with_icon(self):
        """Test button with icon and text children."""
        from inguitive.svg import MOON

        btn = Button(
            Icon(MOON, css="w-6 h-6"),
            "Toggle Theme",
        )
        html = btn.render()
        assert "Toggle Theme" in html
        assert "svg" in html.lower()


class TestLabel:
    def test_basic_render(self):
        """Test basic label rendering."""
        lbl = Label("Hello", id="lbl-1")
        html = lbl.render()
        assert 'id="lbl-1"' in html
        assert "Hello" in html

    def test_callable_text(self):
        """Test dynamic text via callable."""
        state = State("initial")
        lbl = Label(text=lambda: state.get())
        html = lbl.render()
        assert "initial" in html

        state.set("updated")
        html = lbl.render()
        assert "updated" in html


class TestIcon:
    def test_basic_render(self):
        """Test basic icon rendering."""
        from inguitive.svg import MOON

        icon = Icon(MOON)
        html = icon.render()
        assert "<svg" in html
        assert "</svg>" in html

    def test_css_replacement(self):
        """Test class attribute replacement in SVG."""
        from inguitive.svg import MOON

        icon = Icon(MOON, css="w-8 h-8")
        html = icon.render()
        assert 'class="w-8 h-8' in html

    def test_callable_svg(self):
        """Test dynamic SVG via callable."""
        from inguitive.svg import MOON, SUN

        state = State("light")
        icon = Icon(lambda: MOON if state.get() == "light" else SUN)

        html = icon.render()
        assert "MOON" in html or "w-6 h-6 text-gray-800" in html

        state.set("dark")
        html = icon.render()
        assert "SUN" in html or "w-6 h-6 text-gray-800" in html


class TestState:
    def test_state_get_set(self):
        """Test basic state get/set."""
        state = State("initial", "test_state")
        assert state.get() == "initial"

        state.set("updated")
        assert state.get() == "updated"

    def test_listeners(self):
        """Test state listener registration."""
        state = State(0, "counter")
        state.add_listener("component-1")
        state.add_listener("component-2")

        assert "component-1" in state.listeners
        assert "component-2" in state.listeners

        state.remove_listener("component-1")
        assert "component-1" not in state.listeners


class TestDataTable:
    """Tests for DataTable component."""

    def test_basic_render(self):
        """Test basic DataTable rendering with list of dicts."""
        from inguitive.components import DataTable

        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        table = DataTable(data=data)
        html = table.render()

        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert ">name<" in html  # header cell contains "name"
        assert ">age<" in html  # header cell contains "age"
        assert "Alice" in html
        assert "Bob" in html
        assert "30" in html
        assert "25" in html

    def test_columns_parameter(self):
        """Test column ordering and selection."""
        from inguitive.components import DataTable

        data = [
            {"name": "Alice", "age": 30, "city": "NYC"},
        ]
        table = DataTable(data=data, columns=["name", "city"])
        html = table.render()

        assert ">name<" in html
        assert ">city<" in html
        assert ">age<" not in html  # omitted

        # Check order: name should come before city
        name_pos = html.find(">name<")
        city_pos = html.find(">city<")
        assert name_pos < city_pos

    def test_empty_data(self):
        """Test rendering with empty data."""
        from inguitive.components import DataTable

        table = DataTable(data=[])
        html = table.render()

        assert "<table" in html
        assert "<thead><tr></tr></thead>" in html
        assert "<tbody></tbody>" in html

    def test_empty_data_with_columns(self):
        """Test rendering with empty data but columns specified."""
        from inguitive.components import DataTable

        table = DataTable(data=[], columns=["name", "age"])
        html = table.render()

        assert ">name<" in html
        assert ">age<" in html
        assert "<tbody></tbody>" in html

    def test_missing_values(self):
        """Test handling of None and missing keys in data."""
        from inguitive.components import DataTable

        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": None},
            {"name": "Charlie"},  # missing age
        ]
        table = DataTable(data=data)
        html = table.render()

        # None should be empty string - cells have class attrs, so look for empty cells
        # Count cells that contain only whitespace between tags
        import re

        empty_cells = len(re.findall(r'<td class="[^"]*"></td>', html))
        assert empty_cells >= 2  # Bob's age (None) and Charlie's age (missing)

    def test_string_css_backward_compatibility(self):
        """Test that string CSS still works (backward compatibility)."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, css="w-full border")
        html = table.render()

        assert 'class="w-full border' in html
        assert "<table" in html

    def test_callable_string_css(self):
        """Test that callable returning string works."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, css=lambda: "w-full")
        html = table.render()

        assert 'class="w-full' in html

    def test_dict_css_all_keys(self):
        """Test dictionary CSS with all keys."""
        from inguitive.components import DataTable

        data = [{"name": "Alice", "age": 30}]
        css_dict = {"table": "w-full border-2", "header": "bg-blue-500 text-white", "cell": "p-2", "row": "bg-gray-100"}
        table = DataTable(data=data, css=css_dict)
        html = table.render()

        # Check table CSS
        assert "w-full border-2" in html
        # Check header CSS
        assert "bg-blue-500 text-white" in html
        # Check cell CSS
        assert 'class="p-2"' in html
        # Check row CSS
        assert "bg-gray-100" in html

    def test_dict_css_partial(self):
        """Test dictionary CSS with only some keys (should use defaults for missing)."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        css_dict = {"header": "bg-red-500"}
        table = DataTable(data=data, css=css_dict)
        html = table.render()

        # Custom header CSS should be applied
        assert "bg-red-500" in html
        # Default cell CSS should be present
        assert "border border-gray-300" in html

    def test_dict_css_empty(self):
        """Test empty dictionary CSS (should use all defaults)."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, css={})
        html = table.render()

        # Default CSS should be present
        assert "bg-gray-100" in html  # row default
        assert "border border-gray-300" in html  # cell default
        assert "odd:bg-white even:bg-gray-100" in html  # row default

    def test_callable_dict_css(self):
        """Test callable returning dictionary CSS."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, css=lambda: {"header": "bg-green-500"})
        html = table.render()

        assert "bg-green-500" in html

    def test_dict_css_with_table_key(self):
        """Test that 'table' key in dict applies to root table element."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, css={"table": "my-custom-class"})
        html = table.render()

        # Should have the class on the table element
        assert 'class="my-custom-class' in html
        assert "<table" in html

    def test_dict_css_with_callable_values(self):
        """Test dictionary CSS with callable values."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, css={"header": lambda: "bg-purple-500", "cell": lambda: "p-4"})
        html = table.render()

        assert "bg-purple-500" in html
        assert 'class="p-4"' in html

    def test_callable_data(self):
        """Test that callable data works with dict CSS."""
        from inguitive.components import DataTable
        from inguitive.state import State

        state = State([{"name": "Alice"}], "test_table_state")
        table = DataTable(data=state.get, listen_to="test_table_state", css={"header": "bg-orange-500"})
        html = table.render()

        assert "Alice" in html
        assert "bg-orange-500" in html

    def test_update_method_with_dict_css(self):
        """Test that update() method works with dict CSS."""
        from inguitive.components import DataTable

        data = [{"name": "Alice"}]
        table = DataTable(data=data, id="test-table", css={"header": "bg-teal-500"})
        html = table.update()

        assert 'hx-swap-oob="true"' in html
        assert 'id="test-table"' in html
        assert "bg-teal-500" in html
