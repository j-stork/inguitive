"""Tests for async page and trigger handlers in inguitive."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from inguitive import UI, Button, Div, SessionState, State, Text, get_form_data, update_components


class TestAsyncPageHandlers:
    """Tests for async page handlers."""

    def test_async_page_handler(self):
        """Test that async page handlers work correctly."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/async-page")
        async def async_page():
            return ui.page(Div(Text("Async Page")))

        client = TestClient(app)
        response = client.get("/async-page")
        assert response.status_code == 200
        assert "Async Page" in response.text

    def test_async_page_handler_with_state(self):
        """Test that async page handlers can access and display state."""
        app = FastAPI()
        ui = UI(app)
        message_state = State("Async Hello", "message_state")

        @app.get("/async-state-page")
        async def async_state_page():
            return ui.page(Div(Text(lambda: message_state.get())))

        client = TestClient(app)
        response = client.get("/async-state-page")
        assert response.status_code == 200
        assert "Async Hello" in response.text

    def test_async_page_handler_returns_component(self):
        """Test that async page handlers can return Component instances."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/async-component")
        async def async_component_page():
            return ui.page(Div(Text("Async Component"), Button("Click me")))

        client = TestClient(app)
        response = client.get("/async-component")
        assert response.status_code == 200
        assert "Async Component" in response.text
        assert "Click me" in response.text


class TestAsyncTriggerHandlers:
    """Tests for async trigger handlers."""

    def test_async_trigger_handler_with_form_data(self):
        """Test that async trigger handlers can read form data via get_form_data."""
        app = FastAPI()
        ui = UI(app)
        received = {}

        @ui.trigger_handler
        async def async_handle_form(request: Request):
            received.update(await get_form_data(request))
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/async_handle_form", data={"key": "value"})
        assert response.status_code == 200
        assert received["key"] == "value"

    def test_async_trigger_handler_with_state(self):
        """Test that async trigger handlers can update state."""
        app = FastAPI()
        ui = UI(app)
        counter_state = SessionState(0, "counter_state")

        @app.get("/async-counter")
        def counter_page():
            return ui.page(Div(
                Text(lambda: f"Count: {counter_state.get()}", listen_to=counter_state),
                id="async-counter-display",
            ))

        @ui.trigger_handler
        async def async_increment():
            counter_state.set(counter_state.get() + 1)
            return update_components("async-counter-display")

        client = TestClient(app)

        # Initial page load
        response = client.get("/async-counter")
        assert "Count: 0" in response.text

        # Trigger async increment
        client.post("/_trigger/async_increment")

        # Refresh page
        response = client.get("/async-counter")
        assert "Count: 1" in response.text

    def test_async_trigger_handler_with_request(self):
        """Test that async trigger handlers can receive request parameter."""
        app = FastAPI()
        ui = UI(app)
        received_path = None

        @ui.trigger_handler
        async def async_handler_with_request(request):
            nonlocal received_path
            received_path = request.url.path
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/async_handler_with_request")
        assert response.status_code == 200
        assert received_path == "/_trigger/async_handler_with_request"

    def test_async_trigger_handler_complex_form_data(self):
        """Test async trigger handler with nested/structured form data."""
        app = FastAPI()
        ui = UI(app)
        received = {}

        @ui.trigger_handler
        async def async_complex_handler(request: Request):
            received.update(await get_form_data(request))
            return "OK"

        client = TestClient(app)
        response = client.post(
            "/_trigger/async_complex_handler",
            data={
                "user_name": "John",
                "user_email": "john@example.com",
                "settings_theme": "dark",
                "settings_notifications": "enabled",
            },
        )
        assert response.status_code == 200
        assert received["user_name"] == "John"
        assert received["user_email"] == "john@example.com"
        assert received["settings_theme"] == "dark"
        assert received["settings_notifications"] == "enabled"


class TestAsyncIntegration:
    """Integration tests for async handlers."""

    def test_multiple_async_handlers(self):
        """Test that multiple async handlers can be registered on the same app."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/async-page-1")
        async def async_page_1():
            return ui.page(Div(Text("Async Page 1")))

        @app.get("/async-page-2")
        async def async_page_2():
            return ui.page(Div(Text("Async Page 2")))

        @ui.trigger_handler
        async def async_trigger_1():
            return "OK"

        @ui.trigger_handler
        async def async_trigger_2():
            return "OK"

        client = TestClient(app)

        # Test async pages
        response = client.get("/async-page-1")
        assert response.status_code == 200
        assert "Async Page 1" in response.text

        response = client.get("/async-page-2")
        assert response.status_code == 200
        assert "Async Page 2" in response.text

        # Test async triggers
        response = client.post("/_trigger/async_trigger_1")
        assert response.status_code == 200

        response = client.post("/_trigger/async_trigger_2")
        assert response.status_code == 200

    def test_mixed_sync_and_async_handlers(self):
        """Test that sync and async handlers can coexist on the same app."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/sync-page")
        def sync_page():
            return ui.page(Div(Text("Sync Page")))

        @app.get("/async-page")
        async def async_page():
            return ui.page(Div(Text("Async Page")))

        @ui.trigger_handler
        def sync_trigger():
            return "OK"

        @ui.trigger_handler
        async def async_trigger():
            return "OK"

        client = TestClient(app)

        # Test sync page
        response = client.get("/sync-page")
        assert response.status_code == 200
        assert "Sync Page" in response.text

        # Test async page
        response = client.get("/async-page")
        assert response.status_code == 200
        assert "Async Page" in response.text

        # Test sync trigger
        response = client.post("/_trigger/sync_trigger")
        assert response.status_code == 200

        # Test async trigger
        response = client.post("/_trigger/async_trigger")
        assert response.status_code == 200
