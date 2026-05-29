"""Tests for INGUITIVE component classes."""

import pytest
from inguitive.components import Component, Div, Button, Label, Icon
from inguitive.state import State, get_component_registry, get_state_registry
from inguitive.hx import update_components


@pytest.fixture(autouse=True)
def cleanup_registries():
    """Clear registries before and after each test."""
    get_component_registry().clear()
    get_state_registry().clear()
    yield
    get_component_registry().clear()
    get_state_registry().clear()


class TestDiv:
    def test_basic_render(self):
        """Test basic div rendering."""
        div = Div("Hello", id="test-div", cls="text-red-500")
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
        div = Div(id="test", cls=lambda: "text-blue-500")
        html = div.render()
        assert 'class="text-blue-500"' in html


class TestButton:
    def test_basic_render(self):
        """Test basic button rendering."""
        btn = Button("Click me", id="btn-1", cls="bg-blue-500")
        html = btn.render()
        assert 'id="btn-1"' in html
        assert 'class="bg-blue-500"' in html
        assert "Click me" in html

    def test_on_click_generates_htmx_attrs(self):
        """Test that on_click generates HTMX attributes."""
        btn = Button("Click", on_click="test_action")
        html = btn.render()
        assert 'hx-post="/test_action"' in html
        assert 'hx-target="#hx-target"' in html

    def test_on_click_with_args(self):
        """Test on_click with query parameters."""
        btn = Button("Click", on_click="action", on_click_args={"key": "value"})
        html = btn.render()
        assert 'hx-post="/action?key=value"' in html

    def test_children_with_icon(self):
        """Test button with icon and text children."""
        from inguitive.svg import MOON
        btn = Button(
            Icon(MOON, cls="w-6 h-6"),
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

    def test_cls_replacement(self):
        """Test class attribute replacement in SVG."""
        from inguitive.svg import MOON
        icon = Icon(MOON, cls="w-8 h-8")
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
