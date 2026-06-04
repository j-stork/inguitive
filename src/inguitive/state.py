"""
Reactive state management for INGUITIVE.
"""

from typing import TypeVar, Generic
from inguitive.session import get_state_registry, get_data_registry, get_component_registry

T = TypeVar('T')


class State(Generic[T]):
    """Reactive state container with type safety and optional naming."""
    
    def __init__(self, initial_value: T, name: str = ""):
        self._value = initial_value
        self.name = name
        self.listeners: set[str] = set()  # Component IDs listening to this state
        if name:
            get_state_registry()[name] = self

    def get(self) -> T:
        """Get the current state value."""
        return self._value

    def set(self, new_value: T):
        """Set a new state value."""
        self._value = new_value

    def add_listener(self, component_id: str):
        """Add a component ID to listen for changes."""
        self.listeners.add(component_id)

    def remove_listener(self, component_id: str):
        """Remove a component ID from listeners."""
        self.listeners.discard(component_id)


