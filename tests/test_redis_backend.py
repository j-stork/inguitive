"""Tests for RedisBackend session storage.

These tests require both the redis package and a running Redis server.
They will be automatically skipped if either is not available.
"""

import pytest

# Skip all tests in this file if redis package is not installed
redis = pytest.importorskip("redis")


class TestRedisBackend:
    """Tests for RedisBackend session storage."""

    @staticmethod
    def _check_redis_available():
        """Check if Redis server is available. Returns client if yes, raises to skip if no."""
        try:
            client = redis.Redis.from_url("redis://localhost:6379", db=0, decode_responses=True)
            client.ping()
            return client
        except (redis.ConnectionError, redis.RedisError, OSError):
            pytest.skip("Redis server not available")

    def test_redis_backend_basic_operations(self):
        """Test basic save, get, and delete operations with RedisBackend."""
        self._check_redis_available()

        from inguitive.session import RedisBackend, _create_session

        # Create RedisBackend
        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # Create and save a session
        session = _create_session()
        session.data_registry["test_key"] = "test_value"
        backend.save_session(session)

        # Retrieve the session
        retrieved = backend.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.data_registry["test_key"] == "test_value"

        # Delete the session
        backend.delete_session(session.session_id)
        assert backend.get_session(session.session_id) is None

    def test_redis_backend_session_serialization(self):
        """Test that sessions with data are correctly serialized for Redis."""
        self._check_redis_available()

        from inguitive.session import RedisBackend, _create_session

        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # Create a session with various data types
        session = _create_session()
        session.data_registry["string"] = "value"
        session.data_registry["number"] = 42
        session.data_registry["list"] = [1, 2, 3]
        session.data_registry["dict"] = {"nested": "value"}

        # Save to Redis
        backend.save_session(session)

        # Retrieve and verify data is preserved
        retrieved = backend.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.data_registry["string"] == "value"
        assert retrieved.data_registry["number"] == 42
        assert retrieved.data_registry["list"] == [1, 2, 3]
        assert retrieved.data_registry["dict"] == {"nested": "value"}

        # Cleanup
        backend.delete_session(session.session_id)

    def test_redis_backend_ttl(self):
        """Test that sessions expire after the configured TTL."""
        import time

        self._check_redis_available()

        from inguitive.session import RedisBackend, _create_session

        # Use a very short TTL for testing
        backend = RedisBackend(redis_url="redis://localhost:6379", db=0, ttl_seconds=1)

        # Create and save a session
        session = _create_session()
        backend.save_session(session)

        # Verify session exists
        assert backend.get_session(session.session_id) is not None

        # Wait for TTL to expire
        time.sleep(1.5)

        # Session should be gone
        assert backend.get_session(session.session_id) is None

    def test_redis_backend_key_naming(self):
        """Test that Redis keys are correctly formatted."""
        self._check_redis_available()

        from inguitive.session import RedisBackend, _create_session

        client = redis.Redis.from_url("redis://localhost:6379", db=0, decode_responses=True)
        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # Create and save a session
        session = _create_session()
        backend.save_session(session)

        # Check the key in Redis directly
        expected_key = f"inguitive:session:{session.session_id}"
        keys = client.keys("*")
        # There might be other keys, but our key should be there
        our_keys = [k for k in keys if expected_key in k or k == expected_key]
        assert len(our_keys) > 0

        # Cleanup
        backend.delete_session(session.session_id)

    def test_redis_backend_multiple_sessions(self):
        """Test that multiple sessions are stored independently."""
        self._check_redis_available()

        from inguitive.session import RedisBackend, _create_session

        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = _create_session()
            session.data_registry["index"] = i
            backend.save_session(session)
            sessions.append(session)

        # Verify all sessions can be retrieved
        for i, session in enumerate(sessions):
            retrieved = backend.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.data_registry["index"] == i

        # Cleanup
        for session in sessions:
            backend.delete_session(session.session_id)

    def test_redis_backend_cleanup_expired(self):
        """Test that cleanup_expired returns 0 (Redis handles TTL automatically)."""
        self._check_redis_available()

        from inguitive.session import RedisBackend

        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # cleanup_expired should be a no-op and return 0
        result = backend.cleanup_expired()
        assert result == 0

    def test_redis_backend_with_components_not_serialized(self):
        """Test that component_registry and state_registry are not serialized to Redis.

        This test verifies the fix for the serialization bug where Component
        instances could not be JSON-serialized.
        """
        self._check_redis_available()

        from inguitive.components import Button, Div, Text
        from inguitive.session import RedisBackend, _create_session

        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # Create a session and add components to its registries
        session = _create_session()
        session.component_registry["button1"] = Button("Test")
        session.component_registry["div1"] = Div(Text("Test"))
        session.state_registry["state1"] = "some_state"
        session.data_registry["data1"] = "some_data"

        # This should not raise TypeError (the bug we fixed)
        backend.save_session(session)

        # Verify session was saved and can be retrieved
        retrieved = backend.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

        # Component and state registries should be empty (not serialized)
        assert retrieved.component_registry == {}
        assert retrieved.state_registry == {}

        # Only data_registry should have the data
        assert retrieved.data_registry["data1"] == "some_data"

        # Cleanup
        backend.delete_session(session.session_id)

    def test_redis_backend_nonexistent_session(self):
        """Test that getting a nonexistent session returns None."""
        self._check_redis_available()

        from inguitive.session import RedisBackend

        backend = RedisBackend(redis_url="redis://localhost:6379", db=0)

        # Getting a nonexistent session should return None
        assert backend.get_session("nonexistent-session-id") is None

        # Deleting a nonexistent session should not raise
        backend.delete_session("nonexistent-session-id")
