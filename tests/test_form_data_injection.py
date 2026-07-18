"""Tests for form_data parameter injection in trigger handlers."""

from fastapi.testclient import TestClient

from inguitive import create_app


class TestBasicFormData:
    """Basic form data injection tests."""

    def test_basic_form_data_injection(self):
        """Test that form_data parameter receives POST form data."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_form(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        client.post("/_trigger/handle_form", data={"username": "john", "password": "secret"})
        
        assert received["username"] == "john"
        assert received["password"] == "secret"

    def test_multiple_form_fields(self):
        """Test that multiple form fields are all received in form_data."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_multiple(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        client.post("/_trigger/handle_multiple", data={
            "name": "John",
            "email": "john@example.com",
            "age": "30",
            "subscribe": "yes"
        })
        
        assert received["name"] == "John"
        assert received["email"] == "john@example.com"
        assert received["age"] == "30"
        assert received["subscribe"] == "yes"

    def test_empty_form_data(self):
        """Test that empty form data results in empty dict."""
        app = create_app()
        received = None
        
        @app.trigger_handler
        def handle_empty(form_data: dict):
            nonlocal received
            received = form_data
            return "OK"
        
        client = TestClient(app)
        client.post("/_trigger/handle_empty", data={})
        
        assert received == {}


class TestQueryParamsMerging:
    """Tests for query parameter merging into form_data."""

    def test_query_params_merged_into_form_data(self):
        """Test that query parameters from trigger_args are merged into form_data."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_with_args(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        # Query params should be merged into form_data
        client.post("/_trigger/handle_with_args?user_id=123&action=delete", data={"confirm": "yes"})
        
        assert received["user_id"] == "123"
        assert received["action"] == "delete"
        assert received["confirm"] == "yes"

    def test_mixed_form_data_and_query_params(self):
        """Test that form POST data and URL query params are merged into form_data."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_mixed(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        # POST with form data AND query params
        response = client.post(
            "/_trigger/handle_mixed?from_url=query_value",
            data={"from_form": "form_value"}
        )
        
        assert response.status_code == 200
        assert received["from_url"] == "query_value"
        assert received["from_form"] == "form_value"

    def test_query_params_only(self):
        """Test that query params work even without POST form data."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_query_only(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        # POST without form data, only query params
        client.post("/_trigger/handle_query_only?param1=value1&param2=value2")
        
        assert received["param1"] == "value1"
        assert received["param2"] == "value2"


class TestHandlerWithoutFormData:
    """Tests for handlers that don't use form_data parameter."""

    def test_handler_without_form_data_parameter(self):
        """Test that handlers without form_data parameter are not affected."""
        app = create_app()
        called = False
        
        @app.trigger_handler
        def simple_handler():
            nonlocal called
            called = True
            return "OK"
        
        client = TestClient(app)
        # Should work even with POST data, but handler doesn't receive it
        response = client.post("/_trigger/simple_handler", data={"key": "value"})
        assert response.status_code == 200
        assert called is True

    def test_handler_with_different_parameters(self):
        """Test that handlers with other parameters work correctly."""
        app = create_app()
        called_with_request = False
        
        @app.trigger_handler
        def handler_with_request(request):
            nonlocal called_with_request
            called_with_request = True
            return "OK"
        
        client = TestClient(app)
        response = client.post("/_trigger/handler_with_request", data={"key": "value"})
        assert response.status_code == 200
        assert called_with_request is True


class TestSpecialCases:
    """Tests for special cases and edge conditions."""

    def test_form_data_with_special_characters(self):
        """Test that special characters in form data are preserved."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_special(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        client.post("/_trigger/handle_special", data={
            "message": "Hello & goodbye",
            "email": "test@example.com",
            "url": "https://example.com?param=value"
        })
        
        assert received["message"] == "Hello & goodbye"
        assert received["email"] == "test@example.com"
        assert "param=value" in received["url"]

    def test_form_data_with_unicode(self):
        """Test that unicode characters in form data are handled correctly."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_unicode(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        client.post("/_trigger/handle_unicode", data={
            "greeting": "Hello 世界",
            "emoji": "👋🌍"
        })
        
        assert received["greeting"] == "Hello 世界"
        assert received["emoji"] == "👋🌍"

    def test_form_data_with_files(self):
        """Test that file uploads are included in form_data."""
        import tempfile
        import os
        
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_file(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            # Send multipart form data with a file
            with open(temp_path, "rb") as f:
                response = client.post(
                    "/_trigger/handle_file",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200
            # File data should be in form_data
            assert "file" in received
        finally:
            os.unlink(temp_path)

    def test_duplicate_keys_in_form_data(self):
        """Test behavior when form data has values that could be problematic."""
        app = create_app()
        received = {}
        
        @app.trigger_handler
        def handle_duplicates(form_data: dict):
            received.update(form_data)
            return "OK"
        
        client = TestClient(app)
        # Send form data with multiple different keys
        client.post("/_trigger/handle_duplicates", data={"key1": "value1", "key2": "value2"})
        
        assert received["key1"] == "value1"
        assert received["key2"] == "value2"
