"""Tests for @app.page and @app.trigger_handler decorator wiring in inguitive."""


from fastapi.testclient import TestClient

from inguitive import Div, State, Text, create_app, update_components


class TestPageDecorator:
    """Tests for @app.page decorator wiring."""

    def test_page_decorator_registration(self):
        """Test that @app.page registers the route correctly."""
        app = create_app()

        @app.page("/test")
        def test_page():
            return Div(Text("Test Page"))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert "Test Page" in response.text

    def test_page_decorator_root_path(self):
        """Test that @app.page(\"/\") registers at the root path."""
        app = create_app()

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Root" in response.text

    def test_page_decorator_custom_path(self):
        """Test that @app.page works with various custom paths."""
        app = create_app()

        @app.page("/custom/path")
        def custom_page():
            return Div(Text("Custom Path"))

        client = TestClient(app)
        response = client.get("/custom/path")
        assert response.status_code == 200
        assert "Custom Path" in response.text


class TestTriggerHandlerDecorator:
    """Tests for @app.trigger_handler decorator wiring."""

    def test_trigger_handler_decorator_registration(self):
        """Test that @app.trigger_handler registers the POST route correctly."""
        app = create_app()

        @app.trigger_handler
        def increment():
            return "OK"

        client = TestClient(app)
        # Trigger handlers are POSTed to /_trigger/{name}
        response = client.post("/_trigger/increment")
        assert response.status_code == 200

    def test_trigger_handler_with_custom_name(self):
        """Test that @app.trigger_handler(\"custom_name\") uses the custom name."""
        app = create_app()

        @app.trigger_handler("custom_trigger")
        def my_handler():
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/custom_trigger")
        assert response.status_code == 200

    def test_trigger_handler_form_data_injection(self):
        """Test that form_data is correctly injected into trigger handlers."""
        app = create_app()
        received_data = {}

        @app.trigger_handler
        def handle_form(form_data: dict):
            received_data.update(form_data)
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form", data={"key": "value"})
        assert response.status_code == 200
        assert received_data.get("key") == "value"

    def test_trigger_handler_async(self):
        """Test that async trigger handlers work correctly."""
        app = create_app()

        @app.trigger_handler
        async def async_trigger():
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/async_trigger")
        assert response.status_code == 200


class TestMultipleDecorators:
    """Tests for multiple decorators on the same app."""

    def test_multiple_page_routes(self):
        """Test that multiple @app.page routes can be registered."""
        app = create_app()

        @app.page("/page1")
        def page1():
            return Div(Text("Page 1"))

        @app.page("/page2")
        def page2():
            return Div(Text("Page 2"))

        client = TestClient(app)

        response1 = client.get("/page1")
        assert response1.status_code == 200
        assert "Page 1" in response1.text

        response2 = client.get("/page2")
        assert response2.status_code == 200
        assert "Page 2" in response2.text

    def test_multiple_trigger_handlers(self):
        """Test that multiple @app.trigger_handler routes can be registered."""
        app = create_app()

        @app.trigger_handler("trigger1")
        def handler1():
            return "Handler 1"

        @app.trigger_handler("trigger2")
        def handler2():
            return "Handler 2"

        client = TestClient(app)

        response1 = client.post("/_trigger/trigger1")
        assert response1.status_code == 200

        response2 = client.post("/_trigger/trigger2")
        assert response2.status_code == 200

    def test_page_and_trigger_coexistence(self):
        """Test that @app.page and @app.trigger_handler can coexist on the same app."""
        app = create_app()

        @app.page("/test-page")
        def test_page():
            return Div(Text("Test Page"))

        @app.trigger_handler("test-trigger")
        def test_trigger():
            return "OK"

        client = TestClient(app)

        # Test page route
        response = client.get("/test-page")
        assert response.status_code == 200
        assert "Test Page" in response.text

        # Test trigger route
        response = client.post("/_trigger/test-trigger")
        assert response.status_code == 200


class TestStateIntegration:
    """Tests for decorator integration with state management."""

    def test_page_with_state(self):
        """Test that pages can access and display state."""
        app = create_app()
        message_state = State("Hello", "message_state")

        @app.page("/state-test")
        def state_page():
            return Div(Text(lambda: message_state.get()))

        client = TestClient(app)
        response = client.get("/state-test")
        assert response.status_code == 200
        assert "Hello" in response.text

    def test_trigger_with_state_update(self):
        """Test that triggers can update state and pages reflect the changes."""
        app = create_app()
        counter_state = State(0, "counter_state")

        @app.page("/counter-test")
        def counter_page():
            return Div(
                Text(lambda: f"Count: {counter_state.get()}", listen_to="counter_state"),
                id="counter-display"
            )

        @app.trigger_handler
        def increment():
            counter_state.set(counter_state.get() + 1)
            return update_components("counter-display")

        client = TestClient(app)

        # Initial page load
        response = client.get("/counter-test")
        assert "Count: 0" in response.text

        # Trigger increment
        client.post("/_trigger/increment")

        # Refresh page
        response = client.get("/counter-test")
        assert "Count: 1" in response.text

    def test_trigger_handler_with_form_data_and_state(self):
        """Test that trigger handlers can receive form data and update state."""
        app = create_app()
        form_state = State({}, "form_state")

        @app.trigger_handler
        def submit_form(form_data: dict):
            form_state.set(form_data)
            return update_components(*form_state.listeners)

        @app.page("/form-test")
        def form_page():
            return Div(
                Text(lambda: f"Name: {form_state.get().get('name', '')}", listen_to="form_state"),
                id="form-display"
            )

        client = TestClient(app)

        # Submit form
        client.post("/_trigger/submit_form", data={"name": "Test User"})

        # Check page reflects the state
        response = client.get("/form-test")
        assert response.status_code == 200
        assert "Name: Test User" in response.text


class TestPageTitles:
    """Tests for page title functionality."""

    def test_default_title(self):
        """Test that default title 'inguitive' is used when no title is specified."""
        app = create_app()

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "<title>inguitive</title>" in response.text

    def test_app_level_title(self):
        """Test that custom app-level title works."""
        app = create_app(title="My App")

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "<title>My App</title>" in response.text

    def test_page_level_title(self):
        """Test that page-level title via @app.page decorator works."""
        app = create_app()

        @app.page("/login", title="Login Page")
        def login():
            return Div(Text("Login"))

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        assert "<title>Login Page</title>" in response.text

    def test_page_level_title_overrides_app_title(self):
        """Test that page title overrides app title."""
        app = create_app(title="My App")

        @app.page("/login", title="Login Page")
        def login():
            return Div(Text("Login"))

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        assert "<title>Login Page</title>" in response.text

    def test_title_fallback_chain(self):
        """Test the complete title fallback chain: page -> app -> default."""
        # Test app-level fallback to default
        app1 = create_app()

        @app1.page("/test1")
        def test1():
            return Div(Text("Test 1"))

        client1 = TestClient(app1)
        response1 = client1.get("/test1")
        assert "<title>inguitive</title>" in response1.text

        # Test app-level title
        app2 = create_app(title="Custom App")

        @app2.page("/test2")
        def test2():
            return Div(Text("Test 2"))

        client2 = TestClient(app2)
        response2 = client2.get("/test2")
        assert "<title>Custom App</title>" in response2.text

        # Test page-level override
        @app2.page("/test3", title="Page Title")
        def test3():
            return Div(Text("Test 3"))

        response3 = client2.get("/test3")
        assert "<title>Page Title</title>" in response3.text

    def test_title_in_rendered_html(self):
        """Test that title appears correctly in the rendered HTML."""
        app = create_app(title="Test App")

        @app.page("/title-test", title="Title Test Page")
        def title_test():
            return Div(Text("Content"))

        client = TestClient(app)
        response = client.get("/title-test")
        assert response.status_code == 200
        # Verify the title tag is properly formatted
        assert "<title>Title Test Page</title>" in response.text
        # Verify content is still rendered
        assert "Content" in response.text

    def test_mixed_titles(self):
        """Test that different pages can have different titles."""
        app = create_app(title="Default App")

        @app.page("/")
        def root():
            return Div(Text("Root"))

        @app.page("/login", title="Login")
        def login():
            return Div(Text("Login"))

        @app.page("/about", title="About Us")
        def about():
            return Div(Text("About"))

        client = TestClient(app)

        # Root should use app title
        response = client.get("/")
        assert "<title>Default App</title>" in response.text

        # Login should use page title
        response = client.get("/login")
        assert "<title>Login</title>" in response.text

        # About should use page title
        response = client.get("/about")
        assert "<title>About Us</title>" in response.text
