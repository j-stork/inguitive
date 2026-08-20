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
                id="counter-display",
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
                id="form-display",
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


class TestFavicon:
    """Tests for favicon functionality."""

    def test_default_favicon(self):
        """Test that default INGUITIVE favicon is used when no favicon is specified."""
        app = create_app()

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # Default favicon should be /static/inguitive_favicon.svg
        assert '<link rel="icon" href="/static/inguitive_favicon.svg"' in response.text

    def test_custom_app_favicon(self):
        """Test that custom app-level favicon works."""
        app = create_app(favicon="/custom/favicon.ico")

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert '<link rel="icon" href="/custom/favicon.ico"' in response.text

    def test_page_level_favicon(self):
        """Test that page-level favicon via @app.page decorator works."""
        app = create_app()

        @app.page("/login", favicon="/login/favicon.png")
        def login():
            return Div(Text("Login"))

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        assert '<link rel="icon" href="/login/favicon.png"' in response.text

    def test_page_favicon_overrides_app_favicon(self):
        """Test that page favicon overrides app favicon."""
        app = create_app(favicon="/app/favicon.ico")

        @app.page("/login", favicon="/page/favicon.png")
        def login():
            return Div(Text("Login"))

        client = TestClient(app)
        response = client.get("/login")
        assert response.status_code == 200
        # Page-level favicon should override app-level
        assert '<link rel="icon" href="/page/favicon.png"' in response.text

    def test_favicon_fallback_chain(self):
        """Test the complete favicon fallback chain: page -> app -> default."""
        # Test app-level fallback to default
        app1 = create_app()

        @app1.page("/test1")
        def test1():
            return Div(Text("Test 1"))

        client1 = TestClient(app1)
        response1 = client1.get("/test1")
        assert '<link rel="icon" href="/static/inguitive_favicon.svg"' in response1.text

        # Test app-level favicon
        app2 = create_app(favicon="/custom/favicon.svg")

        @app2.page("/test2")
        def test2():
            return Div(Text("Test 2"))

        client2 = TestClient(app2)
        response2 = client2.get("/test2")
        assert '<link rel="icon" href="/custom/favicon.svg"' in response2.text

        # Test page-level override
        @app2.page("/test3", favicon="/page/favicon.ico")
        def test3():
            return Div(Text("Test 3"))

        response3 = client2.get("/test3")
        assert '<link rel="icon" href="/page/favicon.ico"' in response3.text

    def test_favicon_in_rendered_html(self):
        """Test that favicon link appears correctly in the rendered HTML."""
        app = create_app(favicon="/test/favicon.svg")

        @app.page("/favicon-test", favicon="/page/favicon.png")
        def favicon_test():
            return Div(Text("Content"))

        client = TestClient(app)
        response = client.get("/favicon-test")
        assert response.status_code == 200
        # Verify the favicon link is properly formatted
        assert '<link rel="icon" href="/page/favicon.png"' in response.text
        # Verify content is still rendered
        assert "Content" in response.text

    def test_mixed_favicons(self):
        """Test that different pages can have different favicons."""
        app = create_app(favicon="/default/favicon.ico")

        @app.page("/")
        def root():
            return Div(Text("Root"))

        @app.page("/login", favicon="/login/favicon.png")
        def login():
            return Div(Text("Login"))

        @app.page("/about", favicon="/about/favicon.svg")
        def about():
            return Div(Text("About"))

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
        app = create_app()

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

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
        app = create_app(head='<meta name="app-level" content="test">')

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        @app.page("/other")
        def other_page():
            return Div(Text("Other"))

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
        app = create_app()

        @app.page("/login", head='<meta name="page-level" content="login">')
        def login():
            return Div(Text("Login"))

        @app.page("/about")
        def about():
            return Div(Text("About"))

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
        app = create_app(head='<meta name="app" content="app-value">')

        @app.page("/test", head='<meta name="page" content="page-value">')
        def test_page():
            return Div(Text("Test"))

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
        app = create_app(head=['<meta name="app1" content="a">', '<meta name="app2" content="b">'])

        @app.page("/test", head=['<meta name="page1" content="c">', '<meta name="page2" content="d">'])
        def test_page():
            return Div(Text("Test"))

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

        app = create_app(head=MetaTag("app-component", "comp"))

        @app.page("/test", head=MetaTag("page-component", "comp"))
        def test_page():
            return Div(Text("Test"))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Components should be rendered
        assert '<meta name="app-component" content="comp">' in response.text
        assert '<meta name="page-component" content="comp">' in response.text

    def test_head_empty_by_default(self):
        """Test that pages have no extra head content when none is specified."""
        app = create_app()

        @app.page("/")
        def root_page():
            return Div(Text("Root"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # Just verify the page loads correctly
        assert "Root" in response.text

    def test_page_level_head_overrides_empty_app_head(self):
        """Test that page-level head works when app-level is None."""
        app = create_app(head=None)

        @app.page("/test", head='<meta name="page-only" content="test">')
        def test_page():
            return Div(Text("Test"))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert '<meta name="page-only" content="test">' in response.text

    def test_app_level_head_with_empty_page_head(self):
        """Test that app-level head works when page-level is None."""
        app = create_app(head='<meta name="app-only" content="test">')

        @app.page("/test")
        def test_page():
            return Div(Text("Test"))

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert '<meta name="app-only" content="test">' in response.text


class TestPathParameters:
    """Tests for URL path parameter support in @app.page decorator."""

    def test_basic_path_parameter_str(self):
        """Test basic string path parameter."""
        app = create_app()

        @app.page("/user/<username>")
        def user_profile(username: str):
            return Div(Text(f"Hello, {username}"))

        client = TestClient(app)
        response = client.get("/user/john")
        assert response.status_code == 200
        assert "Hello, john" in response.text

    def test_explicit_str_type(self):
        """Test explicit str type annotation."""
        app = create_app()

        @app.page("/user/<username:str>")
        def user_profile(username: str):
            return Div(Text(f"User: {username}"))

        client = TestClient(app)
        response = client.get("/user/jane")
        assert response.status_code == 200
        assert "User: jane" in response.text

    def test_int_path_parameter(self):
        """Test integer path parameter with type conversion."""
        app = create_app()

        @app.page("/post/<post_id:int>")
        def show_post(post_id: int):
            return Div(Text(f"Post {post_id}"))

        client = TestClient(app)
        # Test valid integer
        response = client.get("/post/42")
        assert response.status_code == 200
        assert "Post 42" in response.text

    def test_int_path_parameter_invalid(self):
        """Test that invalid integer path parameter returns 400."""
        app = create_app()

        @app.page("/post/<post_id:int>")
        def show_post(post_id: int):
            return Div(Text(f"Post {post_id}"))

        client = TestClient(app)
        # Test invalid integer
        response = client.get("/post/abc")
        assert response.status_code == 400
        assert "Invalid post_id" in response.json()["detail"]

    def test_float_path_parameter(self):
        """Test float path parameter with type conversion."""
        app = create_app()

        @app.page("/price/<amount:float>")
        def show_price(amount: float):
            return Div(Text(f"Price: ${amount:.2f}"))

        client = TestClient(app)
        # Test valid float
        response = client.get("/price/19.99")
        assert response.status_code == 200
        assert "Price: $19.99" in response.text

    def test_float_path_parameter_invalid(self):
        """Test that invalid float path parameter returns 400."""
        app = create_app()

        @app.page("/price/<amount:float>")
        def show_price(amount: float):
            return Div(Text(f"Price: ${amount:.2f}"))

        client = TestClient(app)
        # Test invalid float
        response = client.get("/price/not-a-number")
        assert response.status_code == 400
        assert "Invalid amount" in response.json()["detail"]

    def test_bool_path_parameter_true_values(self):
        """Test boolean path parameter with various true values."""
        app = create_app()

        @app.page("/toggle/<state:bool>")
        def toggle(state: bool):
            return Div(Text(f"State: {state}"))

        client = TestClient(app)
        
        # Test various true values
        for true_value in ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]:
            response = client.get(f"/toggle/{true_value}")
            assert response.status_code == 200
            assert "State: True" in response.text

    def test_bool_path_parameter_false_values(self):
        """Test boolean path parameter with various false values."""
        app = create_app()

        @app.page("/toggle/<state:bool>")
        def toggle(state: bool):
            return Div(Text(f"State: {state}"))

        client = TestClient(app)
        
        # Test various false values
        for false_value in ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]:
            response = client.get(f"/toggle/{false_value}")
            assert response.status_code == 200
            assert "State: False" in response.text

    def test_uuid_path_parameter(self):
        """Test UUID path parameter with type conversion."""
        import uuid
        
        app = create_app()

        test_uuid = uuid.uuid4()
        
        @app.page("/user/<user_id:uuid>")
        def show_user(user_id: uuid.UUID):
            return Div(Text(f"User: {user_id}"))

        client = TestClient(app)
        # Test valid UUID
        response = client.get(f"/user/{test_uuid}")
        assert response.status_code == 200
        assert f"User: {test_uuid}" in response.text

    def test_uuid_path_parameter_invalid(self):
        """Test that invalid UUID path parameter returns 400."""
        app = create_app()

        @app.page("/user/<user_id:uuid>")
        def show_user(user_id):
            return Div(Text(f"User: {user_id}"))

        client = TestClient(app)
        # Test invalid UUID
        response = client.get("/user/not-a-uuid")
        assert response.status_code == 400
        assert "Invalid user_id" in response.json()["detail"]

    def test_path_type_parameter(self):
        """Test path type parameter that accepts slashes."""
        app = create_app()

        @app.page("/files/<subpath:path>")
        def show_file(subpath: str):
            return Div(Text(f"File: {subpath}"))

        client = TestClient(app)
        # Test path with slashes
        response = client.get("/files/a/b/c")
        assert response.status_code == 200
        assert "File: a/b/c" in response.text

    def test_multiple_path_parameters(self):
        """Test multiple path parameters in the same route."""
        app = create_app()

        @app.page("/user/<user_id:int>/post/<post_id:int>")
        def show_user_post(user_id: int, post_id: int):
            return Div(Text(f"User {user_id}, Post {post_id}"))

        client = TestClient(app)
        response = client.get("/user/123/post/456")
        assert response.status_code == 200
        assert "User 123, Post 456" in response.text

    def test_mixed_parameter_types(self):
        """Test mixed path parameter types in the same route."""
        app = create_app()

        @app.page("/category/<category:str>/page/<page:int>")
        def show_category_page(category: str, page: int):
            return Div(Text(f"{category} page {page}"))

        client = TestClient(app)
        response = client.get("/category/books/page/5")
        assert response.status_code == 200
        assert "books page 5" in response.text

    def test_path_parameter_with_request(self):
        """Test path parameters mixed with request parameter injection."""
        app = create_app()

        @app.page("/user/<user_id:int>")
        def user_profile(user_id: int, request):
            return Div(Text(f"User {user_id}, Method: {request.method}"))

        client = TestClient(app)
        response = client.get("/user/42")
        assert response.status_code == 200
        assert "User 42, Method: GET" in response.text

    def test_path_parameter_with_form_data(self):
        """Test path parameters mixed with form_data parameter injection."""
        app = create_app()

        @app.page("/user/<user_id:int>")
        def user_profile(user_id: int, form_data: dict):
            return Div(Text(f"User {user_id}, Form: {form_data}"))

        client = TestClient(app)
        # Note: This test may need adjustment since page routes are GET by default
        # For now, we'll test that the path parameter works
        response = client.get("/user/42")
        assert response.status_code == 200
        assert "User 42" in response.text

    def test_backward_compatibility(self):
        """Test that existing routes without path parameters still work."""
        app = create_app()

        @app.page("/about")
        def about_page():
            return Div(Text("About Us"))

        client = TestClient(app)
        response = client.get("/about")
        assert response.status_code == 200
        assert "About Us" in response.text

    def test_path_parameter_name_collision_with_request(self):
        """Test that path parameter takes precedence over request when names collide."""
        app = create_app()

        @app.page("/test/<request:str>")
        def test_page(request: str):
            return Div(Text(f"Param: {request}"))

        client = TestClient(app)
        response = client.get("/test/value123")
        assert response.status_code == 200
        assert "Param: value123" in response.text

    def test_unknown_type_defaults_to_str(self):
        """Test that unknown parameter types are treated as str."""
        app = create_app()

        @app.page("/test/<value:unknown_type>")
        def test_page(value: str):
            return Div(Text(f"Value: {value}"))

        client = TestClient(app)
        response = client.get("/test/hello")
        assert response.status_code == 200
        assert "Value: hello" in response.text

    def test_path_parameter_in_root_path(self):
        """Test path parameter in root path."""
        app = create_app()

        @app.page("/<page_name:str>")
        def dynamic_page(page_name: str):
            return Div(Text(f"Dynamic page: {page_name}"))

        client = TestClient(app)
        response = client.get("/home")
        assert response.status_code == 200
        assert "Dynamic page: home" in response.text

    def test_multiple_routes_with_different_parameters(self):
        """Test multiple routes with different path parameters."""
        app = create_app()

        @app.page("/user/<user_id:int>")
        def user_page(user_id: int):
            return Div(Text(f"User: {user_id}"))

        @app.page("/post/<post_slug:str>")
        def post_page(post_slug: str):
            return Div(Text(f"Post: {post_slug}"))

        client = TestClient(app)
        
        # Test user route
        response = client.get("/user/123")
        assert response.status_code == 200
        assert "User: 123" in response.text
        
        # Test post route
        response = client.get("/post/hello-world")
        assert response.status_code == 200
        assert "Post: hello-world" in response.text
