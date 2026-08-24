# Components

inguitive provides a set of composable UI components that map to HTML elements.
All components support dynamic attributes via callables and automatic re-rendering
when state changes.

## Common parameters

Every component accepts these parameters:

| Parameter | Type | Description |
|---|---|---|
| `id` | `str \| None` | HTML `id`. Required for state listening and OOB updates. |
| `css` | `str \| Callable \| dict \| None` | Tailwind CSS classes. `DataTable` accepts a dict. |
| `listen_to` | `str \| list[str] \| None` | State name(s) that trigger a re-render. |
| `trigger` | `str \| None` | Trigger handler name for HTMX POST actions. |
| `trigger_args` | `dict[str, str] \| None` | Query parameters sent with the trigger. |

### Dynamic attributes

Any attribute that accepts a string can also accept a zero-argument callable.
The callable is called on every render, enabling reactive values:

```python
Label(
    text=lambda: f"Total: {cart_state.get()['total']}",
    id="cart-total",
    listen_to="cart_state",
)
```

## Layout components

### `Div`

A generic container that renders as `<div>`.

```python
Div(
    Button("Save", trigger="save"),
    Button("Cancel", trigger="cancel"),
    css="flex gap-2 mt-4",
)
```

### `Text`

Renders a `<p>` element. Use for body copy and reactive text blocks.

```python
Text(
    text=lambda: f"Hello, {name_state.get()}!",
    id="greeting",
    listen_to="name_state",
    css="text-lg text-gray-700",
)
```

### `Label`

Renders a `<label>` element. The `for_` parameter sets the `for` attribute
(renamed to avoid the Python keyword conflict).

```python
Label("Email address", for_="email", css="block text-sm font-medium")
```

### `Header`

Renders heading elements `<h1>` through `<h6>`. Use `level` to specify the heading
level (default: 1).

```python
Header("Main Title", level=1)
Header("Section Heading", level=2, css="text-blue-600")
Header(lambda: get_title(), level=3, listen_to="title_state")
```

## Form components

### `Form`

Wraps children in a `<form>` element. Combine with `Input`, `Button`, and
`validate_form` for full form handling.

```python
Form(
    Input(id="username", type="text", placeholder="Username"),
    Input(id="password", type="password", placeholder="Password"),
    Button("Sign in", trigger="sign_in"),
    css="space-y-4",
)
```

### `Input`

Renders `<input>`. The `type` parameter maps to the HTML `type` attribute.

```python
Input(id="email", type="email", placeholder="you@example.com", css="border rounded p-2 w-full")
Input(id="age",   type="number", value="0")
```

### `Textarea`

Renders `<textarea>`. Use `rows` to control height.

```python
Textarea(id="bio", placeholder="Tell us about yourself", rows=5, css="border rounded p-2 w-full")
```

### `Select`

Renders `<select>` with `<option>` elements. Pass `options` as a list of
`(value, label)` tuples or plain strings.

```python
Select(
    id="country",
    options=[("us", "United States"), ("de", "Germany"), ("gb", "United Kingdom")],
    value="de",
    css="border rounded p-2",
)
```

### `Checkbox`

Renders `<input type="checkbox">`. Use `checked` for the initial state.

```python
Checkbox(id="agree", checked=False, css="mr-2")
```

### `Radio`

Renders `<input type="radio">`. Group buttons with a shared `name`.

```python
Radio(id="size-sm", name="size", value="sm")
Radio(id="size-lg", name="size", value="lg")
```

### `Button`

Renders `<button>`. Wire it to a trigger handler with `trigger`.

```python
from css import BUTTON_PRIMARY_CSS, BUTTON_SECONDARY_CSS

Button("Save",   trigger="save_form",   css=BUTTON_PRIMARY_CSS)
Button("Cancel", trigger="cancel_form", css=BUTTON_SECONDARY_CSS)
```

## Navigation

### `Link`

Renders a semantic `<a>` element for traditional navigation. Prefer `Link` over
a triggered button when the URL should change, the page should be bookmarkable,
or the user might open it in a new tab.

```python
Link("Home",          href="/",     css="text-blue-600 hover:underline")
Link("Documentation", href="/docs", css="text-blue-600 hover:underline")
```

| | `Link(href=...)` | `trigger=...` |
|---|---|---|
| Renders | `<a href="...">` | HTMX POST |
| URL changes | ✅ | ❌ |
| Open in new tab | ✅ | ❌ |
| Partial update | ❌ | ✅ |

## Data display

### `DataTable`

Renders a sortable, filterable `<table>`. Pass `data` as a list of dicts and
`columns` as an ordered list of keys.

```python
DataTable(
    id="users-table",
    data=lambda: users_state.get(),
    columns=["name", "email", "role"],
    listen_to="users_state",
    css={
        "table":  "w-full border-collapse",
        "header": "bg-gray-100 text-left px-4 py-2 font-semibold",
        "row":    "border-t hover:bg-gray-50",
        "cell":   "px-4 py-2",
    },
)
```

### `Icon`

Renders inline SVG. Wrap developer-supplied SVG strings or use the bundled
icon constants from `inguitive.svg`.

```python
from inguitive import Icon
from svg import MOON, SUN

Icon(SUN, css="w-5 h-5 text-yellow-400")
Icon(MOON, css="w-5 h-5 text-indigo-300")
```

## Custom components

### `TemplateComponent`

Renders a Jinja2 template. Pass the template string and any context variables
as keyword arguments.

```python
CARD_TEMPLATE = """
<div class="rounded shadow p-4 {{ css }}">
  <h2 class="text-xl font-bold">{{ title }}</h2>
  <p>{{ body }}</p>
</div>
"""

TemplateComponent(
    template=CARD_TEMPLATE,
    css="bg-white",
    title="Welcome",
    body="This is a template component.",
)
```

### `Component` (base class)

Subclass `Component` to create fully custom components with their own `render`
method:

```python
from inguitive import Component

class Badge(Component):
    def __init__(self, text: str, color: str = "blue", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.color = color

    def render(self) -> str:
        return f'<span class="badge bg-{self.color}-100 text-{self.color}-800">{self.text}</span>'
```
