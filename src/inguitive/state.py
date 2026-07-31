"""
Reactive state management for INGUITIVE.
"""

from typing import TypeVar, Generic

T = TypeVar('T')

# --- Registries ---
_component_registry: dict[str, any] = {}  # {id: component_instance}
_state_registry: dict[str, "State"] = {}     # {name: State}
_data_registry: dict[str, any] = {}      # {id: any_data}


def get_component_registry() -> dict[str, any]:
    """Get the global component registry."""
    return _component_registry


def get_state_registry() -> dict[str, "State"]:
    """Get the global state registry."""
    return _state_registry


class State(Generic[T]):
    """Reactive state container with type safety and optional naming."""
    
    def __init__(self, initial_value: T, name: str = ""):
        self._value = initial_value
        self.name = name
        self.listeners: set[str] = set()  # Component IDs listening to this state
        if name:
            _state_registry[name] = self

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


