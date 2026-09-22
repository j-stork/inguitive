# Components

inguitive provides a set of composable UI components that map to HTML elements.
All components support dynamic attributes via callables and automatic re-rendering
when state changes. Pages are composed from these components in Python — no templates.

## Common parameters

Every component accepts these parameters:

| Parameter | Type | Description |
|---|---|---|
| `id` | `str \| None` | HTML `id`. Auto-generated if omitted. Required for OOB updates. |
| `css` | `str \| Callable \| dict \| None` | Tailwind CSS classes. `DataTable` accepts a dict for per-element styling. |
| `listen_to` | `State \| SessionState \| list[...] \| None` | State object(s) that trigger a re-render. Pass the object, not a name string. |
| `trigger` | `Callable \| None` | Trigger handler callable for HTMX POST actions. Pass the function, not a string. |
| `trigger_args` | `dict[str, str] \| None` | Query parameters sent with the trigger. |

### Dynamic attributes

Any attribute that accepts a string can also accept a zero-argument callable.
The callable is called on every render, enabling reactive values:

```python
Text(
    text=lambda: f"Total: {cart_state.get()['total']}",
    id="cart-total",
    listen_to=cart_state,
)
```

Pass the `State` or `SessionState` object directly to `listen_to`. The framework
registers the component as a listener on that object; when `state.set()` is called
the component is re-rendered via an HTMX out-of-band swap.

## Layout components

### `Div`

A generic container that renders as `<div>`.

```python
Div(
    Button("Save", trigger=save),
    Button("Cancel", trigger=cancel),
    css="flex gap-2 mt-4",
)
```

### `Text`

Renders a `<p>` element. Use for body copy and reactive text blocks.

```python
Text(
    text=lambda: f"Hello, {name_state.get()}!",
    id="greeting",
    listen_to=name_state,
    css="text-lg text-gray-700",
)
```

### `Label`

Renders a `<label>` element. The `for_` parameter sets the `for` attribute
(renamed to avoid the Python keyword conflict).

```python
Label("Email address", for_="email", css="block text-sm font-medium")
```

`Label` is kept for form semantics. For general text display, prefer `Text`.

### `Header`

Renders heading elements `<h1>` through `<h6>`. Use `level` to specify the heading
level (default: 1).

```python
Header("Main Title", level=1)
Header("Section Heading", level=2, css="text-blue-600")
Header(lambda: get_title(), level=3, listen_to=title_state)
```

## Form components

### `Form`

Wraps children in a `<form>` element. Combine with `Input`, `Button`, and a
trigger handler for full form handling.

```python
Form(
    Input(id="username", type="text", placeholder="Username"),
    Input(id="password", type="password", placeholder="Password"),
    Button("Sign in", trigger=sign_in),
    css="space-y-4",
)
```

Forms with an `hx-post` trigger automatically reset after successful submission.

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
Button("Save",   trigger=save_form,   css="bg-blue-600 text-white px-4 py-2 rounded")
Button("Cancel", trigger=cancel_form, css="bg-gray-300 px-4 py-2 rounded")
```

Pass the handler callable to `trigger` — the component reads the trigger URL
from the function object and builds the `hx-post` attribute automatically.

## Navigation

### `Anchor`

Renders a semantic `<a>` element for traditional navigation. Prefer `Anchor`
over a triggered button when the URL should change, the page should be
bookmarkable, or the user might open it in a new tab.

```python
Anchor("Home",          href="/",     css="text-blue-600 hover:underline")
Anchor("Documentation", href="/docs", css="text-blue-600 hover:underline")
```

`Anchor` accepts children like `Div` and `Button`, allowing nested components:

```python
Anchor(Icon(HOME_SVG), href="/", css="w-6 h-6")
Anchor([Text("A"), Text("B")], href="/")
```

| | `Anchor(href=...)` | `trigger=...` |
|---|---|---|
| Renders | `<a href="...">` | HTMX POST |
| URL changes | Yes | No |
| Open in new tab | Yes | No |
| Partial update | No | Yes |

The component previously called `Link` is renamed to `Anchor`. The `Link` name
is freed for a future component that renders `<link rel="stylesheet">`.

## Media

### `Image`

Renders an `<img>` element. Both `src` and `alt` accept strings or callables.

```python
Image(src="/static/logo.png", alt="Company Logo", css="h-10 w-auto")
Image(src=lambda: get_avatar_url(), alt="User Avatar", css="rounded-full h-12 w-12")
Image(src="/static/hero.jpg", alt="Hero", loading="lazy", width="800", height="400")
```

## Data display

### `DataTable`

Renders a `<table>` from a list of dictionaries. Pass `data` as a list of dicts
and `columns` as an ordered list of keys. Both accept callables for reactive
data.

```python
DataTable(
    id="users-table",
    data=lambda: users_state.get(),
    columns=["name", "email", "role"],
    listen_to=users_state,
    css={
        "table":  "w-full border-collapse",
        "header": "bg-gray-100 text-left px-4 py-2 font-semibold",
        "row":    "border-t hover:bg-gray-50",
        "cell":   "px-4 py-2",
    },
)
```

The `css` dict maps to sub-elements: `"table"` (root), `"header"` (`<th>`),
`"row"` (`<tr>`), and `"cell"` (`<td>`). A plain string applies to the root
`<table>` only.

### `Icon`

Renders inline SVG. Pass developer-supplied SVG strings or use bundled icon
constants.

```python
from inguitive import Icon
from svg import MOON, SUN

Icon(SUN, css="w-5 h-5 text-yellow-400")
Icon(MOON, css="w-5 h-5 text-indigo-300")
```

SVG markup is emitted verbatim (markup-safe), so the `css` you pass is applied
to the `<svg>` element.

## Custom components

### `TemplateComponent`

Renders a Jinja2 template. Pass the template string and any context variables
as keyword arguments. Autoescaping is on, matching the safety of the built-in
components.

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

Context values can be callables — they are resolved on every render, so live
state flows in automatically:

```python
TemplateComponent(
    template='<span>{{ value }}</span>',
    value=my_state.get,
    listen_to=my_state,
)
```

`TemplateComponent` is the escape hatch for complex HTML structures that would
be tedious to rebuild with components. It keeps the `jinja2` dependency.

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

Custom components inherit `listen_to`, `trigger`, `trigger_args`, `id`, `css`,
dynamic-attribute resolution, and OOB-update support from the base class.
