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

    def _get_attrs_str(self) -> str:
        """Convert attributes to HTML string, handling cls -> class conversion"""
        filtered_attrs = {k: v for k, v in self.attrs.items() if k != 'cls'}
        if self.cls:
            filtered_attrs['class'] = self.cls
        return " ".join(f'{k}="{v}"' for k, v in filtered_attrs.items())

    def render(self) -> str:
        raise NotImplementedError


class Div(Component):
    def __init__(self, children=None, cls: str = "", **attrs):
        super().__init__(cls=cls, **attrs)
        self.children = children or []

    def render(self) -> str:
        attrs = self._get_attrs_str()
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
        attrs = self._get_attrs_str()
        return f"<button {attrs}>{self.text}</button>"


class Label(Component):
    def __init__(self, text: str, cls: str = "", **attrs):
        super().__init__(cls=cls, **attrs)
        self.text = text

    def render(self) -> str:
        attrs = self._get_attrs_str()
        return f"<p {attrs}>{self.text}</p>"


# --- Counter-Component (with HTMX) ---
def Counter():
    return Div([
        # Label with ID for HTMX targeting
        Label(f"Count: {counter_state['count']}", id="counter-label", cls="text-xl"),
        # Button with HTMX attributes
        Button(
            "+1",
            **{
                "hx-post": "/increment",
                "hx-target": "#hx-target",
                "hx-swap-oob": "true",
                "cls": "bg-blue-500 text-white p-2 rounded mt-2"
            }
        ),
        # Reset button
        Button(
            "Reset",
            **{
                "hx-post": "/reset",
                "hx-target": "#hx-target",
                "hx-swap-oob": "true",
                "cls": "bg-red-500 text-white p-2 rounded mt-2"
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
    # Return OOB HTML to update the label
    return f'<p id="counter-label" class="text-xl" hx-swap-oob="true">Count: {counter_state["count"]}</p>'


@app.post("/reset", response_class=HTMLResponse)
def reset():
    counter_state["count"] = 0
    # Return OOB HTML to update the label
    return f'<p id="counter-label" class="text-xl" hx-swap-oob="true">Count: {counter_state["count"]}</p>'


# --- Start ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
