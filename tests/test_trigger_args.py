"""Tests for get_trigger_args() functionality."""

from fastapi.testclient import TestClient

from inguitive import create_app, get_trigger_args


class TestGetTriggerArgsBasic:
    """Basic tests for get_trigger_args() functionality."""

    def test_trigger_args_accessed_via_get_trigger_args(self):
        """Test that trigger_args are accessible via get_trigger_args()."""
        app = create_app()
        received_args = {}

        @app.trigger_handler
        def handler_with_trigger_args():
            received_args.update(get_trigger_args())
            return "OK"

        client = TestClient(app)
        # Query params simulate trigger_args from Component
        client.post("/_trigger/handler_with_trigger_args?column=name&order=asc")

        assert received_args["column"] == "name"
        assert received_args["order"] == "asc"

    def test_empty_trigger_args_returns_empty_dict(self):
        """Test that get_trigger_args() returns empty dict when no query params."""
        app = create_app()
        received = None

        @app.trigger_handler
        def handler_no_args():
            nonlocal received
            received = get_trigger_args()
            return "OK"

        client = TestClient(app)
        client.post("/_trigger/handler_no_args")

        assert received == {}


class TestQueryParameterExtraction:
    """Tests for extracting trigger_args from URL query params."""

    def test_single_trigger_arg(self):
        """Test accessing a single trigger argument."""
        app = create_app()
        result = None

        @app.trigger_handler
        def single_arg_handler():
            nonlocal result
            result = get_trigger_args().get("key")
            return "OK"

        client = TestClient(app)
        client.post("/_trigger/single_arg_handler?key=value")

        assert result == "value"

    def test_multiple_trigger_args(self):
        """Test accessing multiple trigger arguments."""
        app = create_app()
        result = {}

        @app.trigger_handler
        def multi_arg_handler():
            result.update(get_trigger_args())
            return "OK"

        client = TestClient(app)
        client.post("/_trigger/multi_arg_handler?col1=val1&col2=val2&col3=val3")

        assert result["col1"] == "val1"
        assert result["col2"] == "val2"
        assert result["col3"] == "val3"

    def test_trigger_args_with_post_form_data(self):
        """Test that trigger_args (query params) work alongside POST form data."""
        app = create_app()
        trigger_result = {}
        form_result = {}

        @app.trigger_handler
        def mixed_handler(form_data: dict):
            trigger_result.update(get_trigger_args())
            form_result.update(form_data)
            return "OK"

        client = TestClient(app)
        client.post(
            "/_trigger/mixed_handler?trigger_param=trigger_value",
            data={"form_param": "form_value"}
        )

        assert trigger_result["trigger_param"] == "trigger_value"
        assert form_result["form_param"] == "form_value"


class TestContextIsolation:
    """Tests for context isolation between requests."""

    def test_trigger_args_context_isolation(self):
        """Test that trigger_args from one request don't affect another."""
        app = create_app()
        results = []

        @app.trigger_handler
        def isolation_handler():
            results.append(get_trigger_args().copy())
            return "OK"

        client = TestClient(app)

        # First request with args
        client.post("/_trigger/isolation_handler?first=1")

        # Second request with different args
        client.post("/_trigger/isolation_handler?second=2")

        # Third request with no args
        client.post("/_trigger/isolation_handler")

        assert len(results) == 3
        assert results[0] == {"first": "1"}
        assert results[1] == {"second": "2"}
        assert results[2] == {}

    def test_async_trigger_args_context_isolation(self):
        """Test context isolation with async handlers."""
        app = create_app()
        results = []

        @app.trigger_handler
        async def async_isolation_handler():
            results.append(get_trigger_args().copy())
            return "OK"

        client = TestClient(app)

        # First async request
        client.post("/_trigger/async_isolation_handler?async=1")

        # Second async request
        client.post("/_trigger/async_isolation_handler?async=2")

        assert len(results) == 2
        assert results[0] == {"async": "1"}
        assert results[1] == {"async": "2"}


class TestBackwardCompatibility:
    """Tests ensuring old form_data pattern still works."""

    def test_trigger_args_and_form_data_coexist(self):
        """Test that get_trigger_args() works alongside form_data parameter."""
        app = create_app()
        trigger_values = {}
        form_values = {}

        @app.trigger_handler
        def coexist_handler(form_data: dict):
            trigger_values.update(get_trigger_args())
            form_values.update(form_data)
            return "OK"

        client = TestClient(app)
        client.post(
            "/_trigger/coexist_handler?trigger_key=trigger_val",
            data={"form_key": "form_val"}
        )

        assert trigger_values["trigger_key"] == "trigger_val"
        assert form_values["form_key"] == "form_val"

    def test_form_data_pattern_still_works(self):
        """Test backward compatibility: form_data pattern continues to work."""
        app = create_app()
        received = {}

        @app.trigger_handler
        def old_pattern_handler(form_data: dict):
            received.update(form_data)
            return "OK"

        client = TestClient(app)
        # Query params should be merged into form_data (existing behavior)
        client.post("/_trigger/old_pattern_handler?query=qvalue", data={"post": "pvalue"})

        assert received["query"] == "qvalue"
        assert received["post"] == "pvalue"


class TestEdgeCases:
    """Edge case tests for get_trigger_args()."""

    def test_trigger_args_with_special_characters(self):
        """Test that special characters in trigger_args are handled correctly."""
        app = create_app()
        result = {}

        @app.trigger_handler
        def special_chars_handler():
            result.update(get_trigger_args())
            return "OK"

        client = TestClient(app)
        # TestClient URL-encodes special characters
        client.post("/_trigger/special_chars_handler?param=hello%20world%21")

        assert result["param"] == "hello world!"

    def test_trigger_args_with_various_types(self):
        """Test that trigger_args values are always strings (from URL params)."""
        app = create_app()
        result = {}

        @app.trigger_handler
        def types_handler():
            result.update(get_trigger_args())
            return "OK"

        client = TestClient(app)
        client.post("/_trigger/types_handler?id=123&active=true&rate=1.5")

        # All values should be strings
        assert result["id"] == "123"
        assert result["active"] == "true"
        assert result["rate"] == "1.5"
        assert isinstance(result["id"], str)
        assert isinstance(result["active"], str)
        assert isinstance(result["rate"], str)

    def test_get_trigger_args_outside_handler(self):
        """Test that get_trigger_args() returns empty dict when called outside context."""
        # Call get_trigger_args() outside of any trigger handler context
        result = get_trigger_args()
        assert result == {}


class TestComponentIntegration:
    """Integration tests with Components that use trigger_args."""

    def test_button_trigger_args_integration(self):
        """Test that Button component's trigger_args work with get_trigger_args()."""
        app = create_app()
        received_column = None

        @app.trigger_handler
        def sort_handler():
            nonlocal received_column
            received_column = get_trigger_args().get("column")
            return "OK"

        # Manually trigger the handler with query params (simulating Button click)
        client = TestClient(app)
        client.post("/_trigger/sort_handler?column=name")

        assert received_column == "name"
