# INGUITIVE

A pure Python web framework combining intuitive syntax with **HTMX** for partial page reloads and **Tailwind CSS** for styling.

## Features

- **Reactive State Management**: Components automatically re-render when state changes
- **HTMX Integration**: Out-of-band swaps for seamless partial page updates
- **Component-Based**: Composable UI components with clean Python syntax
- **Dynamic Attributes**: All component attributes can be static strings or callables
- **Type Safe**: Full type hints throughout the codebase
- **Tailwind CSS**: First-class support for utility-first styling

## Quick Start

### Installation

```bash
pip install inguitive
```

### Basic Example

```python
from inguitive import Div, Button, Label, State, create_app
from inguitive.fastapi import BUTTON_PRIMARY_CSS

# Create reactive state
count_state = State(0, "count")

# Define a component
def Counter():
    return Div(
        Label(text=lambda: f"Count: {count_state.get()}", id="count-label", listen_to="count"),
        Button("+1", on_click="increment", cls=BUTTON_PRIMARY_CSS),
    )

# Create FastAPI app
app = create_app()

@app.post("/increment")
def increment():
    count_state.set(count_state.get() + 1)
    from inguitive.htmx import update_components
    return update_components(*count_state.listeners)
```

## Project Structure

```
.
├── src/
│   └── inguitive/
│       ├── __init__.py      # Public API
│       ├── components.py    # Component classes
│       ├── state.py         # Reactive state
│       ├── hx.py             # HTMX helpers
│       ├── fastapi.py       # FastAPI integration
│       └── svg.py           # SVG icon definitions
├── examples/
│   └── counter_app.py       # Demo application
├── tests/
│   └── test_*.py           # Test files
├── pyproject.toml           # Build configuration
└── README.md
```

## Running the Demo

```bash
# From the repository root
uvicorn examples.counter_app:app --reload

# Then open http://localhost:8000
```

## License

MIT License - see [LICENSE](LICENSE) for details.
