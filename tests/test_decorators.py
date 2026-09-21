"""Tests for @app.get + ui.page() and @ui.trigger_handler wiring in inguitive."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from inguitive import Div, SessionState, State, Text, UI, update_components


class TestPageDecorator:
    """Tests for ui.page() inside @app.get routes."""

    def test_page_decorator_registration(self):
        """Test that @app.get + ui.page() registers the route correctly."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/test")
        def test_page():
            return ui.page(Div(Text("Test Page")))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert "Test Page" in response.text

    def test_page_decorator_root_path(self):
        """Test that @app.get("/") registers at the root path."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Root" in response.text

    def test_page_decorator_custom_path(self):
        """Test that @app.get works with various custom paths."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/custom/path")
        def custom_page():
            return ui.page(Div(Text("Custom Path")))

        client = TestClient(app)
        response = client.get("/custom/path")
        assert response.status_code == 200
        assert "Custom Path" in response.text


class TestTriggerHandlerDecorator:
    """Tests for @ui.trigger_handler decorator wiring."""

    def test_trigger_handler_decorator_registration(self):
        """Test that @ui.trigger_handler registers the POST route correctly."""
        app = FastAPI()
        ui = UI(app)

        @ui.trigger_handler
        def increment():
            return "OK"

        client = TestClient(app)
        # Trigger handlers are POSTed to /_trigger/{name}
        response = client.post("/_trigger/increment")
        assert response.status_code == 200

    def test_trigger_handler_with_custom_name(self):
        """Test that @ui.trigger_handler("custom_name") uses the custom name."""
        app = FastAPI()
        ui = UI(app)

        @ui.trigger_handler("custom_trigger")
        def my_handler():
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/custom_trigger")
        assert response.status_code == 200

    def test_trigger_handler_form_data_injection(self):
        """Test that form_data is correctly injected into trigger handlers."""
        app = FastAPI()
        ui = UI(app)
        received_data = {}

        @ui.trigger_handler
        def handle_form(form_data: dict):
            received_data.update(form_data)
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form", data={"key": "value"})
        assert response.status_code == 200
        assert received_data.get("key") == "value"

    def test_trigger_handler_async(self):
        """Test that async trigger handlers work correctly."""
        app = FastAPI()
        ui = UI(app)

        @ui.trigger_handler
        async def async_trigger():
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/async_trigger")
        assert response.status_code == 200


class TestMultipleDecorators:
    """Tests for multiple routes on the same app."""

    def test_multiple_page_routes(self):
        """Test that multiple @app.get routes can be registered."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/page1")
        def page1():
            return ui.page(Div(Text("Page 1")))

        @app.get("/page2")
        def page2():
            return ui.page(Div(Text("Page 2")))

        client = TestClient(app)

        response1 = client.get("/page1")
        assert response1.status_code == 200
        assert "Page 1" in response1.text

        response2 = client.get("/page2")
        assert response2.status_code == 200
        assert "Page 2" in response2.text

    def test_multiple_trigger_handlers(self):
        """Test that multiple @ui.trigger_handler routes can be registered."""
        app = FastAPI()
        ui = UI(app)

        @ui.trigger_handler("trigger1")
        def handler1():
            return "Handler 1"

        @ui.trigger_handler("trigger2")
        def handler2():
            return "Handler 2"

        client = TestClient(app)

        response1 = client.post("/_trigger/trigger1")
        assert response1.status_code == 200

        response2 = client.post("/_trigger/trigger2")
        assert response2.status_code == 200

    def test_page_and_trigger_coexistence(self):
        """Test that @app.get and @ui.trigger_handler can coexist on the same app."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/test-page")
        def test_page():
            return ui.page(Div(Text("Test Page")))

        @ui.trigger_handler("test-trigger")
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
    """Tests for route integration with state management."""

    def test_page_with_state(self):
        """Test that pages can access and display state."""
        app = FastAPI()
        ui = UI(app)
        message_state = State("Hello", "message_state")

        @app.get("/state-test")
        def state_page():
            return ui.page(Div(Text(lambda: message_state.get())))

        client = TestClient(app)
        response = client.get("/state-test")
        assert response.status_code == 200
        assert "Hello" in response.text

    def test_trigger_with_state_update(self):
        """Test that triggers can update state and pages reflect the changes."""
        app = FastAPI()
        ui = UI(app)
        counter_state = SessionState(0, "counter_state")

        @app.get("/counter-test")
        def counter_page():
            return ui.page(
                Div(
                    Text(lambda: f"Count: {counter_state.get()}", listen_to=counter_state),
                    id="counter-display",
                )
            )

        @ui.trigger_handler
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
        app = FastAPI()
        ui = UI(app)
        form_state = SessionState({}, "form_state")

        @ui.trigger_handler
        def submit_form(form_data: dict):
            form_state.set(form_data)
            return update_components(*form_state.listeners)

        @app.get("/form-test")
        def form_page():
            return ui.page(
                Div(
                    Text(lambda: f"Name: {form_state.get().get('name', '')}", listen_to=form_state),
                    id="form-display",
                )
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
        app = FastAPI()
        ui = UI(app)

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "<title>inguitive</title>" in response.text

    def test_app_level_title(self):
        """Test that custom app-level title works."""
        app = FastAPI()
        ui = UI(app, title="My App")

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "<title>My App</title>" in response.text

    def test_page_level_title(self):
        """Test that page-level title via ui.page() works."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), title="Login Page")

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        assert "<title>Login Page</title>" in response.text

    def test_page_level_title_overrides_app_title(self):
        """Test that page title overrides app title."""
        app = FastAPI()
        ui = UI(app, title="My App")

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), title="Login Page")

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        assert "<title>Login Page</title>" in response.text

    def test_title_fallback_chain(self):
        """Test the complete title fallback chain: page -> app -> default."""
        # Test app-level fallback to default
        app1 = FastAPI()
        ui1 = UI(app1)

        @app1.get("/test1")
        def test1():
            return ui1.page(Div(Text("Test 1")))

        client1 = TestClient(app1)
        response1 = client1.get("/test1")
        assert "<title>inguitive</title>" in response1.text

        # Test app-level title
        app2 = FastAPI()
        ui2 = UI(app2, title="Custom App")

        @app2.get("/test2")
        def test2():
            return ui2.page(Div(Text("Test 2")))

        client2 = TestClient(app2)
        response2 = client2.get("/test2")
        assert "<title>Custom App</title>" in response2.text

        # Test page-level override
        @app2.get("/test3")
        def test3():
            return ui2.page(Div(Text("Test 3")), title="Page Title")

        response3 = client2.get("/test3")
        assert "<title>Page Title</title>" in response3.text

    def test_title_in_rendered_html(self):
        """Test that title appears correctly in the rendered HTML."""
        app = FastAPI()
        ui = UI(app, title="Test App")

        @app.get("/title-test")
        def title_test():
            return ui.page(Div(Text("Content")), title="Title Test Page")

        client = TestClient(app)
        response = client.get("/title-test")
        assert response.status_code == 200
        # Verify the title tag is properly formatted
        assert "<title>Title Test Page</title>" in response.text
        # Verify content is still rendered
        assert "Content" in response.text

    def test_mixed_titles(self):
        """Test that different pages can have different titles."""
        app = FastAPI()
        ui = UI(app, title="Default App")

        @app.get("/")
        def root():
            return ui.page(Div(Text("Root")))

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), title="Login")

        @app.get("/about")
        def about():
            return ui.page(Div(Text("About")), title="About Us")

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


class TestFavicon:
    """Tests for favicon functionality."""

    def test_default_favicon(self):
        """Test that default INGUITIVE favicon is used when no favicon is specified."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # Default favicon should be /static/inguitive_favicon.svg
        assert '<link rel="icon" href="/static/inguitive_favicon.svg"' in response.text

    def test_custom_app_favicon(self):
        """Test that custom app-level favicon works."""
        app = FastAPI()
        ui = UI(app, favicon="/custom/favicon.ico")

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert '<link rel="icon" href="/custom/favicon.ico"' in response.text

    def test_page_level_favicon(self):
        """Test that page-level favicon via ui.page() works."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), favicon="/login/favicon.png")

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        assert '<link rel="icon" href="/login/favicon.png"' in response.text

    def test_page_favicon_overrides_app_favicon(self):
        """Test that page favicon overrides app favicon."""
        app = FastAPI()
        ui = UI(app, favicon="/app/favicon.ico")

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), favicon="/page/favicon.png")

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        # Page-level favicon should override app-level
        assert '<link rel="icon" href="/page/favicon.png"' in response.text

    def test_favicon_fallback_chain(self):
        """Test the complete favicon fallback chain: page -> app -> default."""
        # Test app-level fallback to default
        app1 = FastAPI()
        ui1 = UI(app1)

        @app1.get("/test1")
        def test1():
            return ui1.page(Div(Text("Test 1")))

        client1 = TestClient(app1)
        response1 = client1.get("/test1")
        assert '<link rel="icon" href="/static/inguitive_favicon.svg"' in response1.text

        # Test app-level favicon
        app2 = FastAPI()
        ui2 = UI(app2, favicon="/custom/favicon.svg")

        @app2.get("/test2")
        def test2():
            return ui2.page(Div(Text("Test 2")))

        client2 = TestClient(app2)
        response2 = client2.get("/test2")
        assert '<link rel="icon" href="/custom/favicon.svg"' in response2.text

        # Test page-level override
        @app2.get("/test3")
        def test3():
            return ui2.page(Div(Text("Test 3")), favicon="/page/favicon.ico")

        response3 = client2.get("/test3")
        assert '<link rel="icon" href="/page/favicon.ico"' in response3.text

    def test_favicon_in_rendered_html(self):
        """Test that favicon link appears correctly in the rendered HTML."""
        app = FastAPI()
        ui = UI(app, favicon="/test/favicon.svg")

        @app.get("/favicon-test")
        def favicon_test():
            return ui.page(Div(Text("Content")), favicon="/page/favicon.png")

        client = TestClient(app)
        response = client.get("/favicon-test")
        assert response.status_code == 200
        # Verify the favicon link is properly formatted
        assert '<link rel="icon" href="/page/favicon.png"' in response.text
        # Verify content is still rendered
        assert "Content" in response.text

    def test_mixed_favicons(self):
        """Test that different pages can have different favicons."""
        app = FastAPI()
        ui = UI(app, favicon="/default/favicon.ico")

        @app.get("/")
        def root():
            return ui.page(Div(Text("Root")))

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), favicon="/login/favicon.png")

        @app.get("/about")
        def about():
            return ui.page(Div(Text("About")), favicon="/about/favicon.svg")

        client = TestClient(app)

        # Root should use app favicon
        response = client.get("/")
        assert '<link rel="icon" href="/default/favicon.ico"' in response.text

        # Login should use page favicon
        response = client.get("/login")
        assert '<link rel="icon" href="/login/favicon.png"' in response.text

        # About should use page favicon
        response = client.get("/about")
        assert '<link rel="icon" href="/about/favicon.svg"' in response.text

    def test_static_favicon_endpoint(self):
        """Test that the default favicon file is actually served via the /static endpoint."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)

        # Test that the static favicon endpoint returns 200
        response = client.get("/static/inguitive_favicon.svg")
        assert response.status_code == 200

        # Test that the response has the correct content type
        assert response.headers["content-type"] == "image/svg+xml"

        # Test that the response body contains SVG content
        assert "<svg" in response.text
        assert "</svg>" in response.text


class TestHeadContent:
    """Tests for head content functionality."""

    def test_app_level_head(self):
        """Test that app-level head content appears on all pages."""
        app = FastAPI()
        ui = UI(app, head='<meta name="app-level" content="test">')

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        @app.get("/other")
        def other_page():
            return ui.page(Div(Text("Other")))

        client = TestClient(app)

        # Check root page
        response = client.get("/")
        assert response.status_code == 200
        assert '<meta name="app-level" content="test">' in response.text

        # Check other page
        response = client.get("/other")
        assert response.status_code == 200
        assert '<meta name="app-level" content="test">' in response.text

    def test_page_level_head(self):
        """Test that page-level head content appears only on that page."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/login")
        def login():
            return ui.page(Div(Text("Login")), head='<meta name="page-level" content="login">')

        @app.get("/about")
        def about():
            return ui.page(Div(Text("About")))

        client = TestClient(app)

        # Check login page has page-level head
        response = client.get("/login")
        assert response.status_code == 200
        assert '<meta name="page-level" content="login">' in response.text

        # Check about page does NOT have page-level head
        response = client.get("/about")
        assert response.status_code == 200
        assert '<meta name="page-level" content="login">' not in response.text

    def test_app_and_page_level_head_concatenation(self):
        """Test that app-level and page-level head content are concatenated with app first."""
        app = FastAPI()
        ui = UI(app, head='<meta name="app" content="app-value">')

        @app.get("/test")
        def test_page():
            return ui.page(Div(Text("Test")), head='<meta name="page" content="page-value">')

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Both should be present
        assert '<meta name="app" content="app-value">' in response.text
        assert '<meta name="page" content="page-value">' in response.text

        # App-level should appear before page-level
        app_pos = response.text.find('<meta name="app" content="app-value">')
        page_pos = response.text.find('<meta name="page" content="page-value">')
        assert app_pos < page_pos, "App-level head content should appear before page-level"

    def test_head_with_list(self):
        """Test that head content can be provided as a list."""
        app = FastAPI()
        ui = UI(app, head=['<meta name="app1" content="a">', '<meta name="app2" content="b">'])

        @app.get("/test")
        def test_page():
            return ui.page(
                Div(Text("Test")),
                head=['<meta name="page1" content="c">', '<meta name="page2" content="d">'],
            )

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # All should be present
        assert '<meta name="app1" content="a">' in response.text
        assert '<meta name="app2" content="b">' in response.text
        assert '<meta name="page1" content="c">' in response.text
        assert '<meta name="page2" content="d">' in response.text

        # Check order: app1, app2, page1, page2
        app1_pos = response.text.find('<meta name="app1" content="a">')
        app2_pos = response.text.find('<meta name="app2" content="b">')
        page1_pos = response.text.find('<meta name="page1" content="c">')
        page2_pos = response.text.find('<meta name="page2" content="d">')
        assert app1_pos < app2_pos < page1_pos < page2_pos

    def test_head_with_component(self):
        """Test that head content can be a Component."""
        from inguitive import Component

        class MetaTag(Component):
            def __init__(self, name, content):
                self.name = name
                self.content = content

            def render(self):
                return f'<meta name="{self.name}" content="{self.content}">'

        app = FastAPI()
        ui = UI(app, head=MetaTag("app-component", "comp"))

        @app.get("/test")
        def test_page():
            return ui.page(Div(Text("Test")), head=MetaTag("page-component", "comp"))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Components should be rendered
        assert '<meta name="app-component" content="comp">' in response.text
        assert '<meta name="page-component" content="comp">' in response.text

    def test_head_empty_by_default(self):
        """Test that pages have no extra head content when none is specified."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/")
        def root_page():
            return ui.page(Div(Text("Root")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # Just verify the page loads correctly
        assert "Root" in response.text

    def test_page_level_head_overrides_empty_app_head(self):
        """Test that page-level head works when app-level is None."""
        app = FastAPI()
        ui = UI(app, head=None)

        @app.get("/test")
        def test_page():
            return ui.page(Div(Text("Test")), head='<meta name="page-only" content="test">')

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert '<meta name="page-only" content="test">' in response.text

    def test_app_level_head_with_empty_page_head(self):
        """Test that app-level head works when page-level is None."""
        app = FastAPI()
        ui = UI(app, head='<meta name="app-only" content="test">')

        @app.get("/test")
        def test_page():
            return ui.page(Div(Text("Test")))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert '<meta name="app-only" content="test">' in response.text
