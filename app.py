from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- FastAPI Setup ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- Simple State (for Demo without Redis) ---
counter_state = {"count": 0}

# --- Components ---
class Component:
    def __init__(self, cls: str = "", **attrs):
        self.cls = cls
        self.attrs = attrs

    def render(self) -> str:
        raise NotImplementedError

class Div(Component):
    def __init__(self, children=None, cls: str = "", **attrs):
        super().__init__(cls=cls, **attrs)
        self.children = children or []

    def render(self) -> str:
        # Remove cls from attrs if present, and add it as class
        filtered_attrs = {k: v for k, v in self.attrs.items() if k != 'cls'}
        if self.cls:
            filtered_attrs['class'] = self.cls
        attrs = " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())
        children_html = "".join(
            child.render() if hasattr(child, "render") else str(child)
            for child in self.children
        )
        return f"<div {attrs}>{children_html}</div>"

class Button(Component):
    def __init__(self, text: str, cls: str = "", **attrs):
        super().__init__(cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        filtered_attrs = {k: v for k, v in self.attrs.items() if k != 'cls'}
        if self.cls:
            filtered_attrs['class'] = self.cls
        attrs = " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())
        return f"<button {attrs}>{self.text}</button>"

class Label(Component):
    def __init__(self, text: str, cls: str = "", **attrs):
        super().__init__(cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        filtered_attrs = {k: v for k, v in self.attrs.items() if k != 'cls'}
        if self.cls:
            filtered_attrs['class'] = self.cls
        attrs = " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())
        return f"<p {attrs}>{self.text}</p>"

# --- Counter-Component (mit HTMX) ---
def Counter():
    return Div([
        # Label mit ID für HTMX-Targeting
        Label(f"Count: {counter_state['count']}", id="counter-label", cls="text-xl"),
        # Button mit HTMX-Attributen
        Button(
            "+1",
            **{
                "hx-post": "/increment",      # POST an /increment
                "hx-target": "#counter-label", # Ziel: das Label mit ID "counter-label"
                "hx-swap": "innerHTML",        # Ersetze nur den Inhalt des Labels
                "cls": "bg-blue-500 text-white p-2 rounded mt-2"
            }
        )
    ], cls="p-4 max-w-xs mx-auto")

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
    # Gib NUR den neuen Inhalt des Labels zurück (kein vollständiges HTML!)
    return f'<p class="text-xl">Count: {counter_state["count"]}</p>'

# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
