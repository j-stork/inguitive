from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import TypeVar, Generic, Callable
from svg import MOON, SUN

# --- Styling constants ---
# Common base styling for all buttons
BUTTON_BASE_CSS = "rounded-md p-2 text-sm font-semibold shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-600 cursor-pointer"

# Primary button (indigo theme)
BUTTON_PRIMARY_CSS = f"{BUTTON_BASE_CSS} bg-slate-600 text-white active:bg-slate-700"

# Secondary button (white theme with gray ring)
BUTTON_SECONDARY_CSS = f"{BUTTON_BASE_CSS} bg-slate-300 text-black active:bg-slate-400"

# --- FastAPI Setup ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- Registries ---
_component_registry = {}  # {id: component_instance}
_state_registry = {}     # {name: State}
_data_registry = {}      # {id: any_data}

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
counter_state = State(0, "counter_state")
theme_state = State("light", "theme_state")

# --- Helper Functions ---
def update_components(*component_ids: str) -> str:
    """Render multiple components as OOB HTML for HTMX updates"""
    html_parts: list[str] = []
    for cid in component_ids:
        if cid in _component_registry:
            html_parts.append(_component_registry[cid].update())
    return "".join(html_parts)


# --- Components ---
class Component:
    def __init__(self, id: str | None = None, cls: str | Callable[[], str] | None = None, 
                 listen_to: str | None = None, **attrs):
        self.id = id
        self.cls = cls
        self.attrs = attrs
        if self.id:
            _component_registry[self.id] = self
        if listen_to and self.id:
            # Register this component as a listener to the state
            if listen_to in _state_registry:
                _state_registry[listen_to].add_listener(self.id)

    def _resolve(self, value: str | Callable[[], str]) -> str:
        """Resolve a potentially dynamic value (callable or static)"""
        return value() if callable(value) else value

    def _get_attrs_str(self) -> str:
        """Convert attributes to HTML string, handling cls -> class conversion and dynamic values"""
        filtered_attrs = {}
        for k, v in self.attrs.items():
            if k != 'cls':
                filtered_attrs[k] = self._resolve(v)
        resolved_cls = self._resolve(self.cls) if self.cls else None
        if resolved_cls:
            filtered_attrs['class'] = resolved_cls
        # Add id if present
        if self.id:
            filtered_attrs['id'] = self.id
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    def __init__(self, *children, id: str | None = None, cls: str | Callable[[], str] | None = None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.children = list(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates"""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"


class Button(Component):
    def __init__(self, *children, id: str | None = None, 
                 cls: str | Callable[[], str] | None = None, 
                 on_click: str | None = None,
                 on_click_args: dict[str, str] | None = None, **attrs):
        # Convert on_click to HTMX attributes with optional query parameters
        if on_click:
            if 'hx-post' not in attrs:
                url = f"/{on_click.lstrip('/')}"
                if on_click_args:
                    url += "?" + "&".join(f"{k}={v}" for k, v in on_click_args.items())
                attrs['hx-post'] = url
            if 'hx-target' not in attrs:
                attrs['hx-target'] = "#hx-target"
        super().__init__(id=id, cls=cls, **attrs)
        self.children = list(children)

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<button {attrs}>{children_html}</button>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates"""
        if not self.id:
            return self.render()
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        children_html = "".join(
            child.render() if hasattr(child, "render") else self._resolve(child)
            for child in self.children
        )
        return f"<button {attrs}>{children_html}</button>"


class Label(Component):
    def __init__(self, text: str | Callable[[], str], id: str | None = None, 
                 cls: str | Callable[[], str] | None = None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        resolved_text = self._resolve(self.text)
        return f"<p {attrs}>{resolved_text}</p>"

    def update(self) -> str:
        """Render with hx-swap-oob for HTMX out-of-band updates"""
        if not self.id:
            return self.render()
        resolved_text = self._resolve(self.text)
        attrs = f'hx-swap-oob="true" {self._get_attrs_str()}'.strip()
        return f"<p {attrs}>{resolved_text}</p>"


class Icon(Component):
    def __init__(self, svg: str | Callable[[], str], cls: str | Callable[[], str] | None = None, **attrs):
        super().__init__(cls=cls, **attrs)
        self.svg = svg

    @staticmethod
    def _replace_class(svg_str: str, cls_value: str) -> str:
        """Replace or insert class attribute in SVG string.
        
        Preserves all other attributes, quote style, and structure.
        
        Args:
            svg_str: The SVG HTML string
            cls_value: The new class value (without quotes)
            
        Returns:
            SVG string with updated class attribute
        """
        # Find class attribute with optional whitespace between class and =
        idx = svg_str.find('class')
        if idx != -1:
            # Move past 'class'
            idx += len('class')
            # Skip whitespace
            while idx < len(svg_str) and svg_str[idx] in ' \t':
                idx += 1
            # Check for '='
            if idx < len(svg_str) and svg_str[idx] == '=':
                idx += 1
                # Skip whitespace after '='
                while idx < len(svg_str) and svg_str[idx] in ' \t':
                    idx += 1
                # Now at the opening quote
                if idx < len(svg_str) and svg_str[idx] in ('"', "'"):
                    quote_char = svg_str[idx]
                    # Find closing quote
                    content_start = idx + 1
                    content_end = svg_str.find(quote_char, content_start)
                    if content_end != -1:
                        # Replace the content between quotes
                        return (svg_str[:content_start] +
                                cls_value +
                                svg_str[content_end:])
        # No class attribute found - insert one
        if svg_str.startswith('<svg'):
            pos = len('<svg')
            return svg_str[:pos] + f' class="{cls_value}"' + svg_str[pos:]
        return f'<svg class="{cls_value}">{svg_str}'

    def render(self) -> str:
        resolved_svg: str = self._resolve(self.svg)
        
        if self.cls:
            resolved_cls: str = self._resolve(self.cls)
            resolved_svg = self._replace_class(resolved_svg, resolved_cls)
        
        return resolved_svg


# --- Dynamic styling functions ---
def get_counter_style() -> str:
    """Dynamic styling based on counter value"""
    count = counter_state.get()
    base = "text-xl text-center"
    if count > 5:
        return f"{base} text-red-500 font-bold"
    elif count < 0:
        return f"{base} text-blue-500"
    return base


def get_theme_bg() -> str:
    """Dynamic background based on theme state"""
    return "bg-slate-100" if theme_state.get() == "light" else "bg-slate-800"


# --- Counter Component ---
def Counter() -> Div:
    return Div(
        Div(
            Div(
                Button(
                    Icon(lambda: MOON if theme_state.get() == "light" else SUN, cls="w-6 h-6"),
                    #lambda: f"Toggle {'Dark' if theme_state.get() == 'light' else 'Light'} Theme",
                    on_click="toggle_theme",
                    id="theme-toggle",
                    cls=f"{BUTTON_SECONDARY_CSS}"
                ),
                cls="w-full flex justify-end",
            ),
            Label(
                text=lambda: f"Count: {counter_state.get()}",
                id="counter-label",
                cls=get_counter_style,
                listen_to="counter_state"
            ),
            Button("+1", on_click="increment", cls=f"{BUTTON_PRIMARY_CSS} w-full"),
            Button("Reset", on_click="reset", cls=f"{BUTTON_SECONDARY_CSS} w-full"),
            id="counter-card",
            cls="overflow-hidden rounded-xl bg-white shadow-lg p-6 space-y-6 w-sm"
        ),
        id="theme-container",
        cls=lambda: f"w-full min-h-screen {get_theme_bg()} flex items-center justify-center",
        listen_to="theme_state"
    )


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "content": Counter().render()}
    )


@app.post("/increment", response_class=HTMLResponse)
def increment() -> str:
    counter_state.set(counter_state.get() + 1)
    return update_components(*counter_state.listeners)


@app.post("/reset", response_class=HTMLResponse)
def reset() -> str:
    counter_state.set(0)
    return update_components(*counter_state.listeners)


@app.post("/toggle_theme", response_class=HTMLResponse)
def toggle_theme() -> str:
    """Toggle between light and dark theme"""
    current: str = theme_state.get()
    new_theme: str = "dark" if current == "light" else "light"
    theme_state.set(new_theme)
    return update_components(*theme_state.listeners)


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
