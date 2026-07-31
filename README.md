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
from inguitive.css import BUTTON_PRIMARY_CSS
from inguitive.htmx import update_components

# Create reactive state
counter_state = State(0, "counter_state")

# Define a component
def Counter():
    return Div(
        Label(text=lambda: f"Count: {counter_state.get()}", id="counter-label", listen_to="counter_state"),
        Button("+1", on_click="increment", cls=BUTTON_PRIMARY_CSS),
    )

# Create FastAPI app
app = create_app()

@app.post("/increment")
def increment():
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)
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
