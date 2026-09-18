"""Tests for the UI class wiring (Task 4.1).

The ``UI(app, ...)`` constructor must synchronously attach session
middleware, the ``/_sse`` endpoint, and the ``/static`` mount to the
user-owned FastAPI app, and store defaults on ``app.state``.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from inguitive import Div, Text, UI


class TestUIConstruction:
    """Tests for UI(app, ...) synchronous wiring."""

    def test_ui_stores_defaults_on_app_state(self):
        """Title, favicon, head, dev_mode land on app.state."""
        app = FastAPI()
        ui = UI(app, title="My App", favicon="/favicon.ico", head="<meta>")
        assert app.state.title == "My App"
        assert app.state.favicon == "/favicon.ico"
        assert app.state.head == "<meta>"
        assert app.state.dev_mode is True

    def test_ui_default_title(self):
        """Default title is 'inguitive' when not specified."""
        app = FastAPI()
        ui = UI(app)
        assert app.state.title == "inguitive"

    def test_ui_registers_sse_route(self):
        """The /_sse GET route is registered by the constructor."""
        app = FastAPI()
        ui = UI(app)
        paths = {route.path for route in app.routes}
        assert "/_sse" in paths

    def test_ui_mounts_static(self):
        """The /static mount is present and returns 404 for missing files."""
        app = FastAPI()
        ui = UI(app)
        client = TestClient(app)
        response = client.get("/static/does_not_exist.txt")
        assert response.status_code == 404

    def test_ui_attaches_session_middleware(self):
        """SessionMiddleware is attached (cookie is set on a page request)."""
        app = FastAPI()
        ui = UI(app)

        @ui.page("/")
        def home():
            return Div(Text("Hello"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # SessionMiddleware sets a session cookie.
        cookies = response.cookies
        assert "inguitive_session_id" in cookies

    def test_ui_page_decorator_serves_html(self):
        """@ui.page('/') renders the component inside the document shell."""
        app = FastAPI()
        ui = UI(app, title="Home Page")

        @ui.page("/")
        def home():
            return Div(Text("Hello World"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Hello World" in response.text
        assert "<title>Home Page</title>" in response.text

    def test_ui_trigger_handler_registers_post_route(self):
        """@ui.trigger_handler registers a POST route at /_trigger/<name>."""
        app = FastAPI()
        ui = UI(app)

        @ui.trigger_handler
        def my_action():
            pass

        client = TestClient(app)
        response = client.post("/_trigger/my_action")
        assert response.status_code == 200

    def test_ui_trigger_handler_with_explicit_name(self):
        """@ui.trigger_handler('name') uses the explicit name."""
        app = FastAPI()
        ui = UI(app)

        @ui.trigger_handler("custom_name")
        def my_action():
            pass

        client = TestClient(app)
        response = client.post("/_trigger/custom_name")
        assert response.status_code == 200
