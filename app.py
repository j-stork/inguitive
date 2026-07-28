from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- FastAPI Setup ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- Component Registry ---
_component_registry = {}  # {id: component_instance}

# --- Simple State ---
counter_state = {"count": 0}

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
    def __init__(self, id=None, cls=None, **attrs):
        self.id = id
        self.cls = cls
        self.attrs = attrs
        if self.id:
            _component_registry[self.id] = self

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
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    def __init__(self, children=None, id=None, cls=None, **attrs):
        super().__init__(id=id, cls=cls, **attrs)
        self.children = children or []

    def render(self) -> str:
        attrs = self._get_attrs_str()
        children_html = "".join(
            child.render() if hasattr(child, "render") else str(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"


class Button(Component):
    def __init__(self, text, id=None, cls=None, **attrs):
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
        # Ensure id is present and add hx-swap-oob
        if 'id=' not in attrs:
            attrs = f'id="{self.id}" {attrs}'.strip()
        attrs = f'hx-swap-oob="true" {attrs}'.strip()
        return f"<p {attrs}>{resolved_text}</p>"


# --- Dynamic styling function ---
def get_counter_style():
    """Dynamic styling based on counter value"""
    count = counter_state['count']
    base = "text-xl"
    if count > 5:
        return f"{base} text-red-500 font-bold"
    elif count < 0:
        return f"{base} text-blue-500"
    return base


# --- Counter Label (fully dynamic) ---
CounterLabel = Label(
    text=lambda: f"Count: {counter_state['count']}",
    id="counter-label",
    cls=get_counter_style  # Can be a function reference or lambda
)


# --- Counter Component ---
def Counter():
    return Div([
        CounterLabel,
        Button(
            "+1",
            **{
                "hx-post": "/increment",
                "hx-target": "#hx-target",
                "cls": "bg-blue-500 text-white p-2 rounded mt-2"
            }
        ),
        Button(
            "Reset",
            **{
                "hx-post": "/reset",
                "hx-target": "#hx-target",
                "cls": "bg-red-500 text-white p-2 rounded mt-2"
            }
        )
    ], id="counter", cls="p-4 max-w-xs mx-auto")


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "content": Counter().render()}
    )


@app.post("/increment", response_class=HTMLResponse)
def increment():
    counter_state["count"] += 1
    return render_components_oob("counter-label")


@app.post("/reset", response_class=HTMLResponse)
def reset():
    counter_state["count"] = 0
    return render_components_oob("counter-label")


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
