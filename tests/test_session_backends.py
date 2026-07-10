"""Tests for session backend implementations in INGUITIVE."""

import json

import pytest

from inguitive.components import Button
from inguitive.session import MemoryBackend, Session, create_session


class TestRedisBackendSerialization:
    """Tests for RedisBackend serialization fixes."""

    def test_session_with_components_serialization(self):
        """Test that sessions with components can be serialized for Redis storage.
        
        This tests the fix for: component_registry and state_registry contain live
        Component instances that cannot be JSON-serialized. The fix excludes these
        from serialization, only persisting session_id and data_registry.
        """
        # Create a session with components in registry
        session = create_session()
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
        session = create_session()
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
        session1 = create_session()
        session1.data_registry['test'] = 'value1'
        backend1.save_session(session1)
        
        # backend2 should NOT have this session
        assert backend2.get_session(session1.session_id) is None
        
        # backend1 should have it
        retrieved1 = backend1.get_session(session1.session_id)
        assert retrieved1 is not None
        assert retrieved1.data_registry['test'] == 'value1'
        
        # Save a session to backend2
        session2 = create_session()
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
        session1 = create_session()
        session2 = create_session()
        session3 = create_session()
        
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
        session = create_session()
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
        session = create_session()
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
        session = create_session()
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
