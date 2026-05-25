from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import TypeVar, Generic

# --- FastAPI Setup ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- Registries ---
_component_registry = {}  # {id: component_instance}
_state_registry = {}     # {name: State}

# --- State Management ---
T = TypeVar('T')

class State(Generic[T]):
    """Reactive state container with type safety and optional naming"""
    def __init__(self, initial_value: T, name: str = ""):
        self._value = initial_value
        self.name = name
        self.listeners: set[str] = set()  # Component IDs listening to this state
        if name:
            _state_registry[name] = self

    def get(self) -> T:
        """Get the current state value"""
        return self._value

    def set(self, new_value: T):
        """Set a new state value"""
        self._value = new_value

    def add_listener(self, component_id: str):
        """Add a component ID to listen for changes"""
        self.listeners.add(component_id)

    def remove_listener(self, component_id: str):
        """Remove a component ID from listeners"""
        self.listeners.discard(component_id)


# --- State Instances ---
counter_state = State(0, "counter")

# --- Helper Functions ---
def render_components_oob(*component_ids):
    """Render multiple components as OOB HTML for HTMX"""
    html_parts = []
    for cid in component_ids:
        if cid in _component_registry:
            component = _component_registry[cid]
            if hasattr(component, 'render_oob'):
                html_parts.append(component.render_oob())
            else:
                html_parts.append(component.render())
    return "".join(html_parts)


# --- Components ---
class Component:
    def __init__(self, id=None, cls=None, listen_to: str | None = None, **attrs):
        self.id = id
        self.cls = cls
        self.attrs = attrs
        if self.id:
            _component_registry[self.id] = self
        if listen_to and self.id:
            # Register this component as a listener to the state
            if listen_to in _state_registry:
                _state_registry[listen_to].add_listener(self.id)

    def _resolve(self, value):
        """Resolve a potentially dynamic value (callable or static)"""
        return value() if callable(value) else value

    def _get_attrs_str(self) -> str:
        """Convert attributes to HTML string, handling cls -> class conversion and dynamic values"""
        filtered_attrs = {}
        for k, v in self.attrs.items():
            if k != 'cls':
                filtered_attrs[k] = self._resolve(v)
        resolved_cls = self._resolve(self.cls)
        if resolved_cls:
            filtered_attrs['class'] = resolved_cls
        # Add id if present
        if self.id:
            filtered_attrs['id'] = self.id
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    def __init__(self, *children, id=None, cls=None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.children = list(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else str(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"


class Button(Component):
    def __init__(self, text, id=None, cls=None, on_click: str | None = None, **attrs):
        # Convert on_click to HTMX attributes
        if on_click:
            if 'hx-post' not in attrs:
                attrs['hx-post'] = f"/{on_click.lstrip('/')}"
            if 'hx-target' not in attrs:
                attrs['hx-target'] = "#hx-target"
        super().__init__(id=id, cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<button {attrs}>{resolved_text}</button>"


class Label(Component):
    def __init__(self, text, id=None, cls=None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<p {attrs}>{resolved_text}</p>"

    def render_oob(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates"""
        if not self.id:
            return self.render()
        resolved_text = self._resolve(self.text)
        attrs = self._get_attrs_str()
        # Add hx-swap-oob attribute
        attrs = f'hx-swap-oob="true" {attrs}'.strip()
        return f"<p {attrs}>{resolved_text}</p>"


# --- Dynamic styling function ---
def get_counter_style():
    """Dynamic styling based on counter value"""
    count = counter_state.get()
    base = "text-xl text-center"
    if count > 5:
        return f"{base} text-red-500 font-bold"
    elif count < 0:
        return f"{base} text-blue-500"
    return base


# --- Counter Component ---
def Counter():
    return Div(
        Label(
            text=lambda: f"Count: {counter_state.get()}",
            id="counter-label",
            cls=get_counter_style,
            listen_to="counter"
        ),
        Button("+1", on_click="increment", cls="bg-blue-500 text-white p-2 rounded-lg mt-2 w-full"),
        Button("Reset", on_click="reset", cls="bg-red-500 text-white p-2 rounded-lg mt-2 w-full"),
        id="counter",
        cls="p-4 max-w-xs mx-auto"
    )


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "content": Counter().render()}
    )


@app.post("/increment", response_class=HTMLResponse)
def increment():
    counter_state.set(counter_state.get() + 1)
    return render_components_oob(*counter_state.listeners)


@app.post("/reset", response_class=HTMLResponse)
def reset():
    counter_state.set(0)
    return render_components_oob(*counter_state.listeners)


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
