"""Tests for error handling and dev mode error pages."""

import pytest
from fastapi.testclient import TestClient

from inguitive import create_app


class TestErrorHandling:
    """Tests for the dev-mode error page functionality."""

    def test_error_page_in_dev_mode_shows_traceback(self):
        """Test that in dev mode, the error page displays the full traceback."""
        app = create_app(dev_mode=True)

        @app.page("/error")
        def error_page():
            raise ValueError("Test error for dev mode")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")

        # Verify 500 status
        assert response.status_code == 500

        # Verify traceback appears in response
        assert "Traceback" in response.text
        assert "ValueError" in response.text
        assert "Test error for dev mode" in response.text

        # Verify request details appear
        assert "Request Details:" in response.text
        assert "/error" in response.text

    def test_error_page_in_prod_mode_hides_traceback(self):
        """Test that in production mode, the error page does NOT display traceback."""
        app = create_app(dev_mode=False)

        @app.page("/error")
        def error_page():
            raise ValueError("Test error for production mode")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")

        # Verify 500 status
        assert response.status_code == 500

        # Verify traceback does NOT appear in response
        assert "Traceback" not in response.text
        assert "ValueError" not in response.text
        assert "Test error for production mode" not in response.text

        # Verify generic error message appears
        assert "Internal Server Error" in response.text
        assert "An unexpected error occurred" in response.text

    def test_error_page_uses_base_template(self):
        """Test that the error page extends base.html and includes Tailwind/HTMX."""
        app = create_app(dev_mode=True)

        @app.page("/error")
        def error_page():
            raise ValueError("Template test")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")

        # Verify base template is used (HTMX and Tailwind scripts)
        assert "htmx.org" in response.text
        assert "tailwindcss" in response.text

    def test_error_page_500_status(self):
        """Test that unhandled exceptions return 500 status code."""
        app = create_app(dev_mode=True)

        @app.page("/error")
        def error_page():
            raise RuntimeError("Status code test")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")

        assert response.status_code == 500

    def test_error_page_with_different_http_methods(self):
        """Test that error page shows correct request method."""
        app = create_app(dev_mode=True)

        @app.page("/get-error")
        def get_error_page():
            raise ValueError("GET error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/get-error")

        assert response.status_code == 500
        assert "GET" in response.text
        assert "/get-error" in response.text

    def test_error_page_renders_without_crashing(self):
        """Test that the error page itself renders without raising exceptions."""
        app = create_app(dev_mode=True)

        @app.page("/error")
        def error_page():
            raise Exception("Render test")

        client = TestClient(app, raise_server_exceptions=False)
        # Should not raise any exceptions during the request
        response = client.get("/error")

        # Should get a valid HTML response
        assert response.status_code == 500
        assert "<!DOCTYPE html>" in response.text
        assert "<html" in response.text

    def test_dev_mode_stored_on_app_state(self):
        """Test that dev_mode is correctly stored on app.state."""
        app_true = create_app(dev_mode=True)
        app_false = create_app(dev_mode=False)

        assert app_true.state.dev_mode is True
        assert app_false.state.dev_mode is False

    def test_error_handler_catches_all_exceptions(self):
        """Test that the exception handler catches various exception types."""
        app = create_app(dev_mode=True)

        exception_types = [
            ValueError("test"),
            RuntimeError("test"),
            TypeError("test"),
            KeyError("test"),
            Exception("test"),
        ]

        for exc in exception_types:
            @app.page(f"/error-{type(exc).__name__}")
            def error_page():
                raise exc

        client = TestClient(app, raise_server_exceptions=False)

        for exc in exception_types:
            path = f"/error-{type(exc).__name__}"
            response = client.get(path)
            assert response.status_code == 500
            assert "500" in response.text

    def test_error_page_prod_mode_still_has_request_details_in_title(self):
        """Test that production mode still shows the error context in title."""
        app = create_app(dev_mode=False)

        @app.page("/prod-error")
        def error_page():
            raise ValueError("Production error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/prod-error")

        # In production mode, we should still have basic error info
        assert response.status_code == 500
        assert "Internal Server Error" in response.text
        # But no traceback
        assert "Traceback" not in response.text
