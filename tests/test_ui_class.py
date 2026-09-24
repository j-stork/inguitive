"""Tests for the UI class wiring (Task 4.1).

The ``UI(app, ...)`` constructor must synchronously attach session
middleware, the ``/_sse`` endpoint, and the ``/static`` mount to the
user-owned FastAPI app, and store defaults on ``app.state``.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from inguitive import UI, Div, SessionMiddleware, Text
from inguitive.fastapi import _tailwind_tag


def test_tailwind_tag_css_emits_link():
    """_tailwind_tag emits a <link> for .css URLs."""
    assert _tailwind_tag("/static/tw.css") == '<link rel="stylesheet" href="/static/tw.css">'


def test_tailwind_tag_js_emits_script():
    """_tailwind_tag emits a <script> for non-.css URLs."""
    assert _tailwind_tag("https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4") == (
        '<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>'
    )


class TestUIConstruction:
    """Tests for UI(app, ...) synchronous wiring."""

    def test_ui_stores_defaults_on_app_state(self):
        """Title, favicon, head, dev_mode land on app.state."""
        app = FastAPI()
        _ui = UI(app, title="My App", favicon="/favicon.ico", head="<meta>")
        assert app.state.title == "My App"
        assert app.state.favicon == "/favicon.ico"
        assert app.state.head == "<meta>"
        assert app.state.dev_mode is True

    def test_ui_default_title(self):
        """Default title is 'inguitive' when not specified."""
        app = FastAPI()
        _ui = UI(app)
        assert app.state.title == "inguitive"

    def test_ui_registers_sse_route(self):
        """The /_sse GET route is registered by the constructor."""
        app = FastAPI()
        _ui = UI(app)
        paths = {route.path for route in app.routes}
        assert "/_sse" in paths

    def test_ui_mounts_static(self):
        """The /static mount is present and returns 404 for missing files."""
        app = FastAPI()
        _ui = UI(app)
        client = TestClient(app)
        response = client.get("/static/does_not_exist.txt")
        assert response.status_code == 404

    def test_ui_auto_adds_session_middleware_by_default(self):
        """By default UI adds SessionMiddleware automatically."""
        app = FastAPI()
        _ui = UI(app)
        middleware_types = {
            getattr(m.cls, "__name__", type(m).__name__) for m in app.user_middleware
        }
        assert "SessionMiddleware" in middleware_types

    def test_ui_configure_session_middleware_false_does_not_add(self):
        """configure_session_middleware=False opts out of the auto-add."""
        app = FastAPI()
        _ui = UI(app, configure_session_middleware=False)
        middleware_types = {
            getattr(m.cls, "__name__", type(m).__name__) for m in app.user_middleware
        }
        assert "SessionMiddleware" not in middleware_types

    def test_ui_page_works_with_default_middleware(self):
        """Default flag: pages set a session cookie automatically."""
        app = FastAPI()
        ui = UI(app)

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hello")))

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

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hello")))

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

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hello")))

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

    def test_ui_startup_check_raises_when_middleware_missing(self):
        """Opt out + forgot: startup itself raises, before any request."""
        import pytest

        app = FastAPI()
        _ui = UI(app, configure_session_middleware=False)

        with pytest.raises(RuntimeError, match="SessionMiddleware"):
            with TestClient(app, raise_server_exceptions=True):
                pass

    def test_ui_startup_check_passes_when_middleware_added_after_opt_out(self):
        """Opt out + did add: startup succeeds, pages work."""
        app = FastAPI()
        ui = UI(app, configure_session_middleware=False)
        app.add_middleware(SessionMiddleware)

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hello")))

        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "Hello" in response.text

    def test_ui_page_renders_component_in_shell(self):
        """ui.page() renders the component inside the document shell."""
        app = FastAPI()
        ui = UI(app, title="Home Page")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hello World")))

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Hello World" in response.text
        assert "<title>Home Page</title>" in response.text

    def test_ui_page_renders_full_document_shell(self):
        """ui.page() emits the full HTML document shell, not just the component.

        Asserts the skeleton that _render_page_shell produces: DOCTYPE, <html>,
        <head> with charset + viewport metas, the <title>, the favicon <link>,
        the HTMX + SSE extension + Tailwind CDN <script> tags, and the hidden
        #hx-target div wired to sse-connect="/_sse". Inter font and the
        @theme style block are no longer in the default output.
        """
        app = FastAPI()
        ui = UI(app, title="Shell Test", favicon="/fav.ico")

        @app.get("/")
        def home():
            return ui.page(Div(Text("body content")))

        client = TestClient(app)
        response = client.get("/")
        html = response.text
        assert html.startswith("<!DOCTYPE html>"), "shell must start with DOCTYPE"
        assert "<html" in html
        assert "<head>" in html
        assert '<meta charset="UTF-8">' in html
        assert '<meta name="viewport"' in html
        assert "<title>Shell Test</title>" in html
        assert '<link rel="icon" href="/fav.ico">' in html
        # HTMX core + SSE extension + Tailwind CDN (all as <script> by default)
        assert "htmx.org@1.9.6" in html
        assert "sse.js" in html
        assert "tailwindcss/browser@4" in html
        # Inter font and @theme style block are no longer in the default shell
        assert "rsms.me/inter" not in html
        assert "text/tailwindcss" not in html
        assert "--font-sans" not in html
        # Hidden SSE auto-connect target
        assert 'id="hx-target"' in html
        assert 'sse-connect="/_sse"' in html
        # Body content is rendered inside the shell
        assert "body content" in html

    def test_ui_page_per_page_title_override(self):
        """Per-page title overrides the UI default."""
        app = FastAPI()
        ui = UI(app, title="Global Title")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")), title="Page Title")

        client = TestClient(app)
        response = client.get("/")
        assert "<title>Page Title</title>" in response.text
        assert "Global Title" not in response.text

    def test_ui_page_per_page_favicon_override(self):
        """Per-page favicon overrides the UI default."""
        app = FastAPI()
        ui = UI(app, favicon="/global.ico")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")), favicon="/page.ico")

        client = TestClient(app)
        response = client.get("/")
        assert '/page.ico' in response.text
        assert '/global.ico' not in response.text

    def test_ui_page_head_merges_global_and_page_by_default(self):
        """replace_global_head=False (default): both global and page head appear."""
        app = FastAPI()
        ui = UI(app, head="<meta name='global'>")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")), head="<meta name='page'>")

        client = TestClient(app)
        response = client.get("/")
        assert "<meta name='global'>" in response.text
        assert "<meta name='page'>" in response.text

    def test_ui_page_replace_global_head_true(self):
        """replace_global_head=True: only page head appears, global is dropped."""
        app = FastAPI()
        ui = UI(app, head="<meta name='global'>")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")), head="<meta name='page'>", replace_global_head=True)

        client = TestClient(app)
        response = client.get("/")
        assert "<meta name='page'>" in response.text
        assert "<meta name='global'>" not in response.text

    def test_ui_page_replace_global_head_true_no_page_head(self):
        """replace_global_head=True with no page head: neither appears."""
        app = FastAPI()
        ui = UI(app, head="<meta name='global'>")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")), replace_global_head=True)

        client = TestClient(app)
        response = client.get("/")
        assert "<meta name='global'>" not in response.text

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

    # ------------------------------------------------------------------
    # Task 1664.6: configurable head assets
    # ------------------------------------------------------------------

    def test_self_hosted_htmx_and_sse(self):
        """htmx_src and sse_ext_src overrides appear in the rendered shell."""
        app = FastAPI()
        ui = UI(
            app,
            htmx_src="/static/htmx.min.js",
            sse_ext_src="/static/sse.js",
        )

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")))

        client = TestClient(app)
        html = client.get("/").text
        assert "/static/htmx.min.js" in html
        assert "/static/sse.js" in html
        assert "unpkg.com" not in html

    def test_tailwind_src_css_emits_link_tag(self):
        """tailwind_src ending in .css emits a <link>, not a <script>."""
        app = FastAPI()
        ui = UI(app, tailwind_src="/static/tw.css")

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")))

        client = TestClient(app)
        html = client.get("/").text
        assert '<link rel="stylesheet" href="/static/tw.css">' in html
        assert "/static/tw.css" not in html.replace(
            '<link rel="stylesheet" href="/static/tw.css">', ""
        )

    def test_tailwind_src_none_omits_tailwind(self):
        """tailwind_src=None omits Tailwind entirely."""
        app = FastAPI()
        ui = UI(app, tailwind_src=None)

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")))

        client = TestClient(app)
        html = client.get("/").text
        assert "tailwind" not in html.lower()

    def test_replace_default_head_emits_no_framework_assets(self):
        """replace_default_head=True emits only meta/title/favicon + head_extra."""
        app = FastAPI()
        ui = UI(
            app,
            replace_default_head=True,
            head=[
                "<script src='/static/htmx.min.js'></script>",
                "<script src='/static/sse.js'></script>",
                "<link rel='stylesheet' href='/static/tw.css'>",
            ],
        )

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")), title="Custom")

        client = TestClient(app)
        html = client.get("/").text
        # User head content is present
        assert "/static/htmx.min.js" in html
        assert "/static/sse.js" in html
        assert "/static/tw.css" in html
        # Framework defaults are absent
        assert "unpkg.com" not in html
        assert "tailwindcss/browser" not in html
        # Title still rendered
        assert "<title>Custom</title>" in html
        # Body still rendered
        assert "Hi" in html

    def test_replace_default_head_missing_htmx_raises(self):
        """replace_default_head=True with no HTMX core script raises RuntimeError."""
        app = FastAPI()
        ui = UI(
            app,
            replace_default_head=True,
            head=[
                "<script src='https://unpkg.com/htmx.org@1.9.6/dist/ext/sse.js'></script>",
            ],
        )

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")))

        client = TestClient(app)
        import pytest

        with pytest.raises(RuntimeError, match="HTMX core script"):
            client.get("/")

    def test_replace_default_head_missing_sse_raises(self):
        """replace_default_head=True with no SSE extension raises RuntimeError."""
        app = FastAPI()
        ui = UI(
            app,
            replace_default_head=True,
            head=[
                "<script src='https://unpkg.com/htmx.org@1.9.6'></script>",
            ],
        )

        @app.get("/")
        def home():
            return ui.page(Div(Text("Hi")))

        client = TestClient(app)
        import pytest

        with pytest.raises(RuntimeError, match="SSE extension"):
            client.get("/")
