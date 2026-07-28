"""Tests for session backend implementations in inguitive."""

import json

from inguitive.components import Button
from inguitive.session import MemoryBackend, Session, _create_session


class TestRedisBackendSerialization:
    """Tests for RedisBackend serialization fixes."""

    def test_session_with_components_serialization(self):
        """Test that sessions with components can be serialized for Redis storage.

        This tests the fix for: component_registry and state_registry contain live
        Component instances that cannot be JSON-serialized. The fix excludes these
        from serialization, only persisting session_id and data_registry.
        """
        # Create a session with components in registry
        session = _create_session()
        session.component_registry['test_button'] = Button('Test')
        session.state_registry['test_state'] = 'some_state'
        session.data_registry['test_data'] = 'some_data'

        # Should serialize without TypeError
        serialized = session.to_dict()
        json_str = json.dumps(serialized)  # This would fail before the fix

        # Verify only session_id and data_registry are serialized
        assert 'session_id' in serialized
        assert 'data_registry' in serialized
        assert 'component_registry' not in serialized
        assert 'state_registry' not in serialized

        # Should deserialize correctly
        deserialized = Session.from_dict(json.loads(json_str))
        assert deserialized.session_id == session.session_id
        assert deserialized.data_registry == session.data_registry
        assert deserialized.component_registry == {}
        assert deserialized.state_registry == {}

    def test_session_with_complex_data_serialization(self):
        """Test serialization with various data types in data_registry."""
        session = _create_session()
        session.data_registry['string'] = 'test'
        session.data_registry['number'] = 42
        session.data_registry['list'] = [1, 2, 3]
        session.data_registry['dict'] = {'key': 'value'}
        session.data_registry['nested'] = {'list': [1, 2], 'dict': {'a': 1}}

        # Should serialize without error
        serialized = session.to_dict()
        json_str = json.dumps(serialized)

        # Should deserialize correctly
        deserialized = Session.from_dict(json.loads(json_str))
        assert deserialized.data_registry == session.data_registry


class TestMemoryBackendInstanceIsolation:
    """Tests for MemoryBackend instance isolation fix."""

    def test_instances_have_isolated_storage(self):
        """Test that MemoryBackend instances do not share session storage.

        This tests the fix for: _sessions was a class-level variable, causing all
        instances to share the same storage. The fix moves _sessions to __init__
        as an instance variable.
        """
        # Create two backend instances
        backend1 = MemoryBackend()
        backend2 = MemoryBackend()

        # Save a session to backend1
        session1 = _create_session()
        session1.data_registry['test'] = 'value1'
        backend1.save_session(session1)

        # backend2 should NOT have this session
        assert backend2.get_session(session1.session_id) is None

        # backend1 should have it
        retrieved1 = backend1.get_session(session1.session_id)
        assert retrieved1 is not None
        assert retrieved1.data_registry['test'] == 'value1'

        # Save a session to backend2
        session2 = _create_session()
        session2.data_registry['test'] = 'value2'
        backend2.save_session(session2)

        # backend1 should still NOT have session2
        assert backend1.get_session(session2.session_id) is None
        # backend2 should have session2
        retrieved2 = backend2.get_session(session2.session_id)
        assert retrieved2 is not None
        assert retrieved2.data_registry['test'] == 'value2'

    def test_multiple_instances_independent(self):
        """Test that operations on one backend don't affect others."""
        backend1 = MemoryBackend()
        backend2 = MemoryBackend()
        backend3 = MemoryBackend()

        # Create sessions in each backend
        session1 = _create_session()
        session2 = _create_session()
        session3 = _create_session()

        backend1.save_session(session1)
        backend2.save_session(session2)
        backend3.save_session(session3)

        # Each backend should only have its own session
        assert backend1.get_session(session1.session_id) is not None
        assert backend1.get_session(session2.session_id) is None
        assert backend1.get_session(session3.session_id) is None

        assert backend2.get_session(session2.session_id) is not None
        assert backend2.get_session(session1.session_id) is None
        assert backend2.get_session(session3.session_id) is None

        assert backend3.get_session(session3.session_id) is not None
        assert backend3.get_session(session1.session_id) is None
        assert backend3.get_session(session2.session_id) is None


class TestMemoryBackendBasicOperations:
    """Tests for basic MemoryBackend operations."""

    def test_save_and_retrieve_session(self):
        """Test basic save and get operations."""
        backend = MemoryBackend()

        # Create and save a session
        session = _create_session()
        session.data_registry['key'] = 'value'
        backend.save_session(session)

        # Retrieve the session
        retrieved = backend.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.data_registry['key'] == 'value'

    def test_delete_session(self):
        """Test session deletion."""
        backend = MemoryBackend()

        # Create and save a session
        session = _create_session()
        backend.save_session(session)

        # Verify it exists
        assert backend.get_session(session.session_id) is not None

        # Delete the session
        backend.delete_session(session.session_id)
        assert backend.get_session(session.session_id) is None

    def test_update_session(self):
        """Test updating an existing session."""
        backend = MemoryBackend()

        # Create and save a session
        session = _create_session()
        session.data_registry['key'] = 'original'
        backend.save_session(session)

        # Modify and save again
        session.data_registry['key'] = 'updated'
        backend.save_session(session)

        # Retrieve and verify update
        retrieved = backend.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.data_registry['key'] == 'updated'

    def test_get_nonexistent_session(self):
        """Test that getting a non-existent session returns None."""
        backend = MemoryBackend()
        assert backend.get_session('nonexistent-id') is None

    def test_delete_nonexistent_session(self):
        """Test that deleting a non-existent session doesn't raise an error."""
        backend = MemoryBackend()
        # Should not raise
        backend.delete_session('nonexistent-id')
        assert backend.get_session('nonexistent-id') is None


class TestMemoryBackendSessionExpiry:
    """Tests for MemoryBackend session expiry and cleanup functionality."""

    def test_session_has_last_accessed_on_creation(self):
        """Test that sessions have last_accessed timestamp set on creation."""
        import time

        from inguitive.session import _create_session

        before = time.time()
        session = _create_session()
        after = time.time()

        assert session.last_accessed >= before
        assert session.last_accessed <= after

    def test_get_session_updates_last_accessed(self):
        """Test that getting a session updates its last_accessed timestamp."""
        import time

        backend = MemoryBackend()
        session = _create_session()
        backend.save_session(session)

        # Ensure some time has passed
        time.sleep(0.01)

        old_timestamp = session.last_accessed
        retrieved = backend.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.last_accessed > old_timestamp

    def test_save_session_updates_last_accessed(self):
        """Test that saving a session updates its last_accessed timestamp."""
        import time

        backend = MemoryBackend()
        session = _create_session()

        # Ensure some time has passed
        time.sleep(0.01)

        old_timestamp = session.last_accessed
        backend.save_session(session)

        assert session.last_accessed > old_timestamp

    def test_cleanup_expired_removes_old_sessions(self):
        """Test that cleanup_expired removes sessions older than TTL."""
        import time

        # Create backend with short TTL for testing
        backend = MemoryBackend(ttl_seconds=1)

        # Create a session
        session = _create_session()
        backend.save_session(session)

        # Verify session exists
        assert backend.get_session(session.session_id) is not None

        # Manually set last_accessed to the past (2 seconds ago) by modifying the stored session
        backend._sessions[session.session_id].last_accessed = time.time() - 2

        # Run cleanup
        deleted_count = backend.cleanup_expired()

        # Session should be deleted
        assert deleted_count == 1
        assert backend.get_session(session.session_id) is None

    def test_cleanup_expired_keeps_recent_sessions(self):
        """Test that cleanup_expired keeps sessions within TTL."""

        # Create backend with TTL of 1 hour
        backend = MemoryBackend(ttl_seconds=3600)

        # Create a session (will have current timestamp)
        session = _create_session()
        backend.save_session(session)

        # Run cleanup
        deleted_count = backend.cleanup_expired()

        # Session should NOT be deleted
        assert deleted_count == 0
        assert backend.get_session(session.session_id) is not None

    def test_cleanup_expired_with_no_expiry(self):
        """Test that cleanup with TTL <= 0 does nothing."""
        backend = MemoryBackend(ttl_seconds=0)

        # Create and save a session with old timestamp
        session = _create_session()
        session.last_accessed = 0.0  # Very old timestamp
        backend.save_session(session)

        # Run cleanup - should not delete anything
        deleted_count = backend.cleanup_expired()

        assert deleted_count == 0
        assert backend.get_session(session.session_id) is not None

    def test_cleanup_expired_multiple_sessions(self):
        """Test cleanup with multiple sessions, some expired, some not."""
        import time

        backend = MemoryBackend(ttl_seconds=1)

        # Create 3 sessions
        session1 = _create_session()  # Recent
        session2 = _create_session()  # Will be expired
        session3 = _create_session()  # Recent

        backend.save_session(session1)
        backend.save_session(session2)
        backend.save_session(session3)

        # Manually set session2 to be expired
        backend._sessions[session2.session_id].last_accessed = time.time() - 2

        # Run cleanup
        deleted_count = backend.cleanup_expired()

        # Only session2 should be deleted
        assert deleted_count == 1
        assert backend.get_session(session1.session_id) is not None
        assert backend.get_session(session2.session_id) is None
        assert backend.get_session(session3.session_id) is not None

    def test_cleanup_expired_returns_correct_count(self):
        """Test that cleanup_expired returns the correct number of deleted sessions."""
        import time

        backend = MemoryBackend(ttl_seconds=1)

        # Create 5 expired sessions
        session_ids = []
        for _ in range(5):
            session = _create_session()
            backend.save_session(session)
            session_ids.append(session.session_id)

        # Manually set all to be expired
        for sid in session_ids:
            backend._sessions[sid].last_accessed = time.time() - 2

        # Run cleanup
        deleted_count = backend.cleanup_expired()

        assert deleted_count == 5

    def test_cleanup_expired_empty_backend(self):
        """Test that cleanup on empty backend returns 0."""
        backend = MemoryBackend(ttl_seconds=1)
        deleted_count = backend.cleanup_expired()
        assert deleted_count == 0

    def test_session_serialization_with_last_accessed(self):
        """Test that last_accessed is serialized and deserialized correctly."""
        import json

        # Create a session
        session = _create_session()
        original_timestamp = session.last_accessed

        # Serialize
        serialized = session.to_dict()
        assert 'last_accessed' in serialized
        assert serialized['last_accessed'] == original_timestamp

        # Deserialize
        json_str = json.dumps(serialized)
        deserialized = Session.from_dict(json.loads(json_str))

        assert deserialized.last_accessed == original_timestamp

    def test_session_deserialization_backward_compatible(self):
        """Test that old session data without last_accessed can be deserialized."""

        # Old session data without last_accessed
        old_data = {
            "session_id": "test-id",
            "data_registry": {"key": "value"},
        }

        # Should not raise
        session = Session.from_dict(old_data)

        # last_accessed should default to 0.0
        assert session.last_accessed == 0.0
        assert session.session_id == "test-id"
        assert session.data_registry == {"key": "value"}

    def test_get_session_updates_timestamp_then_cleanup(self):
        """Integration test: accessing a session keeps it from being cleaned up."""
        import time

        backend = MemoryBackend(ttl_seconds=1)

        # Create a session
        session = _create_session()
        backend.save_session(session)

        # Wait a bit
        time.sleep(0.01)

        # Manually set last_accessed to the past (but within TTL)
        session.last_accessed = time.time() - 0.5
        backend.save_session(session)

        # Now access the session (should update timestamp)
        retrieved = backend.get_session(session.session_id)
        assert retrieved is not None

        # Wait a bit more
        time.sleep(0.01)

        # Manually set timestamp to just before TTL
        retrieved.last_accessed = time.time() - 0.5
        backend.save_session(retrieved)

        # Run cleanup - session should survive because it's within TTL
        deleted_count = backend.cleanup_expired()
        assert deleted_count == 0
        assert backend.get_session(session.session_id) is not None
