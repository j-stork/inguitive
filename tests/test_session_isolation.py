"""Tests for session isolation in INGUITIVE."""

import pytest
from fastapi.testclient import TestClient

# Import after setting up path
from examples.counter_app import app


def get_client():
    """Create a fresh TestClient for each test to ensure clean state."""
    return TestClient(app)


class TestSessionIsolation:
    """Test that user sessions are properly isolated."""

    def test_session_cookie_created(self):
        """Verify that a session cookie is created on first request."""
        client = get_client()
        response = client.get("/")
        assert "inguitive_session_id" in response.cookies
        assert response.cookies["inguitive_session_id"] is not None

    def test_session_id_displayed_in_ui(self):
        """Verify that the session ID is displayed in the UI."""
        client = get_client()
        response = client.get("/")
        assert "Session:" in response.text
        # Session ID should be a UUID-like string
        assert len(response.text) > 0

    def test_independent_counters_across_sessions(self):
        """Verify that two users have independent counter states."""
        # User 1 gets initial page with fresh client
        client1 = get_client()
        response1 = client1.get("/")
        cookies1 = response1.cookies
        assert "Count: 0" in response1.text

        # User 1 increments counter
        client1.post("/_trigger/increment", cookies=cookies1)
        response1 = client1.get("/", cookies=cookies1)
        assert "Count: 1" in response1.text

        # User 2 gets initial page with separate client (no cookies)
        client2 = get_client()
        response2 = client2.get("/")
        cookies2 = response2.cookies
        # User 2 should still have count 0
        assert "Count: 0" in response2.text

        # User 2 increments their counter
        client2.post("/_trigger/increment", cookies=cookies2)
        response2 = client2.get("/", cookies=cookies2)
        assert "Count: 1" in response2.text

        # User 1 should still have count 1 (not affected by User 2)
        response1 = client1.get("/", cookies=cookies1)
        assert "Count: 1" in response1.text

    def test_independent_themes_across_sessions(self):
        """Verify that two users have independent theme states."""
        # User 1 with fresh client
        client1 = get_client()
        response1 = client1.get("/")
        cookies1 = response1.cookies

        # User 1 toggles to dark theme
        client1.post("/_trigger/toggle_theme", cookies=cookies1)
        response1 = client1.get("/", cookies=cookies1)
        # Dark theme should be active (bg-slate-800)
        assert "bg-slate-800" in response1.text

        # User 2 with fresh client should have light theme
        client2 = get_client()
        response2 = client2.get("/")
        cookies2 = response2.cookies
        assert "bg-slate-100" in response2.text

        # User 2 toggles to dark theme
        client2.post("/_trigger/toggle_theme", cookies=cookies2)
        response2 = client2.get("/", cookies=cookies2)
        assert "bg-slate-800" in response2.text

        # User 1 should still have dark theme
        response1 = client1.get("/", cookies=cookies1)
        assert "bg-slate-800" in response1.text

    def test_session_persistence_across_requests(self):
        """Verify that session state persists across multiple requests."""
        client = get_client()
        # User makes initial request
        response1 = client.get("/")
        cookies = response1.cookies
        assert "Count: 0" in response1.text

        # User increments multiple times
        for _ in range(3):
            client.post("/_trigger/increment", cookies=cookies)

        response2 = client.get("/", cookies=cookies)
        assert "Count: 3" in response2.text

        # Reset counter
        client.post("/_trigger/reset", cookies=cookies)
        response3 = client.get("/", cookies=cookies)
        assert "Count: 0" in response3.text

    def test_different_session_ids_for_different_users(self):
        """Verify that different users get different session IDs."""
        client1 = get_client()
        response1 = client1.get("/")
        cookies1 = response1.cookies
        session_id_1 = cookies1.get("inguitive_session_id")

        client2 = get_client()
        response2 = client2.get("/")
        cookies2 = response2.cookies
        session_id_2 = cookies2.get("inguitive_session_id")

        # Two separate clients should get different session IDs
        assert session_id_1 is not None
        assert session_id_2 is not None
        assert session_id_1 != session_id_2
