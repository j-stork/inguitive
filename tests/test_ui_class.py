"""Tests for the UI class wiring (Task 4.1).

The ``UI(app, ...)`` constructor must synchronously attach session
middleware, the ``/_sse`` endpoint, and the ``/static`` mount to the
user-owned FastAPI app, and store defaults on ``app.state``.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from inguitive import Div, Text, UI, SessionMiddleware


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

    def test_ui_auto_adds_session_middleware_by_default(self):
        """By default UI adds SessionMiddleware automatically."""
        app = FastAPI()
        ui = UI(app)
        middleware_types = {
            getattr(m.cls, "__name__", type(m).__name__) for m in app.user_middleware
        }
        assert "SessionMiddleware" in middleware_types

    def test_ui_configure_session_middleware_false_does_not_add(self):
        """configure_session_middleware=False opts out of the auto-add."""
        app = FastAPI()
        ui = UI(app, configure_session_middleware=False)
        middleware_types = {
            getattr(m.cls, "__name__", type(m).__name__) for m in app.user_middleware
        }
        assert "SessionMiddleware" not in middleware_types

    def test_ui_page_works_with_default_middleware(self):
        """Default flag: pages set a session cookie automatically."""
        app = FastAPI()
        ui = UI(app)

        @ui.page("/")
        def home():
            return Div(Text("Hello"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Hello" in response.text
        assert "inguitive_session_id" in response.cookies

    def test_ui_page_works_when_user_adds_middleware_after_opt_out(self):
        """Opt out + explicit add: pages still set a session cookie."""
        app = FastAPI()
        ui = UI(app, configure_session_middleware=False)
        app.add_middleware(SessionMiddleware)

        @ui.page("/")
        def home():
            return Div(Text("Hello"))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Hello" in response.text
        assert "inguitive_session_id" in response.cookies

    def test_ui_page_raises_loud_error_without_middleware(self):
        """Opt out + forgot to add: page request raises an actionable error."""
        import pytest

        app = FastAPI()
        ui = UI(app, configure_session_middleware=False)

        @ui.page("/")
        def home():
            return Div(Text("Hello"))

        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(RuntimeError, match="SessionMiddleware"):
            client.get("/")

    def test_ui_trigger_raises_loud_error_without_middleware(self):
        """Opt out + forgot to add: trigger request raises an actionable error."""
        import pytest

        app = FastAPI()
        ui = UI(app, configure_session_middleware=False)

        @ui.trigger_handler
        def my_action():
            pass

        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(RuntimeError, match="SessionMiddleware"):
            client.post("/_trigger/my_action")

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
