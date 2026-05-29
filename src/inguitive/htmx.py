"""
HTMX helper functions for INGUITIVE.
"""

from inguitive.state import get_component_registry


def update_components(*component_ids: str) -> str:
    """Render multiple components as OOB HTML for HTMX updates.
    
    Args:
        *component_ids: Component IDs to update
        
    Returns:
        Concatenated HTML string with hx-swap-oob attributes
    """
    html_parts: list[str] = []
    component_registry = get_component_registry()
    for cid in component_ids:
        if cid in component_registry:
            html_parts.append(component_registry[cid].update())
    return "".join(html_parts)
