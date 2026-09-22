# Trigger Handlers

Trigger handlers are the server-side functions that respond to user interactions.
inguitive registers an HTMX POST endpoint for each one and returns out-of-band
HTML swaps for any components whose state changed.

Trigger handlers live on the `UI` instance, not the FastAPI app. You decorate
them with `@ui.trigger_handler`:

```python
from fastapi import FastAPI
from inguitive import UI, SessionState

app = FastAPI()
ui = UI(app)

counter = SessionState(0, "counter")


@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)
```

## Basic handlers

```python
@ui.trigger_handler
def save():
    # do something
    pass

@ui.trigger_handler
async def fetch_data():
    result = await some_async_call()
    data_state.set(result)
```

Both sync and async functions are supported. Use `async def` whenever your
handler performs I/O (database queries, HTTP calls, file reads).

## Auto-propagation: returning `None`

A trigger handler typically returns `None`. The framework tracks `State` and
`SessionState` mutations during the handler's execution and, at handler exit,
automatically collects the listener component IDs of every mutated state and
generates the OOB swap response. You do not return OOB HTML — single-state and
multi-state handlers are equally simple:

```python
@ui.trigger_handler
def increment():
    counter.set(counter.get() + 1)
    # returns None — framework auto-generates the OOB swap
```

For the rare case where you need to push a component that was not triggered by
a state change, the explicit `update_components(*ids)` form is still available:

```python
from inguitive import update_components

@ui.trigger_handler
def refresh():
    return update_components("chart", "status-badge")
```

## Wiring a component with `trigger`

Pass the handler callable to a component's `trigger` parameter — not a string.
The component reads the trigger URL from the function object and builds the
`hx-post` attribute automatically:

```python
Button("+1", trigger=increment)
```

## Trigger arguments

Pass data from a component to its handler using `trigger_args` on the component
and `get_trigger_args()` inside the handler:

```python
from inguitive import get_trigger_args

@ui.trigger_handler
def delete_item():
    item_id = get_trigger_args().get("id")
    items.set([i for i in items.get() if i["id"] != item_id])

# In a component:
Button(
    "Delete",
    trigger=delete_item,
    trigger_args={"id": item["id"]},
)
```

`trigger_args` are sent as URL query parameters. `get_trigger_args()` returns
them as `dict[str, str]` — all values are strings, so cast as needed.

## Form data

When a trigger is fired from inside a `<form>`, declare a `request: Request`
parameter and call `get_form_data(request)` to get the submitted fields:

```python
from fastapi import Request
from inguitive import get_form_data

@ui.trigger_handler
async def submit_contact(request: Request):
    form = await get_form_data(request)
    name  = form.get("name", "")
    email = form.get("email", "")
    # process...
```

`get_form_data(request)` is a thin wrapper around `await request.form()` that
returns a `dict[str, str | UploadFile]`. Text inputs come back as `str`; file
inputs come back as `UploadFile`. Unchecked checkboxes do not appear in the
dict (HTML omits them), so use `form.get("field", default)` for optional fields.

## Returning HTML

Trigger handlers can return an HTML string that inguitive injects into the page.
This is useful for flash messages, confirmation banners, or any content that is
not tied to a listening component:

```python
@ui.trigger_handler
def submit():
    # ... process ...
    return '<p class="text-green-600">Saved successfully!</p>'
```

The returned HTML is appended to the HTMX response alongside any OOB swaps.

## Redirecting

inguitive no longer ships a `redirect()` helper. Use FastAPI's
`RedirectResponse` directly:

```python
from fastapi import RedirectResponse

@ui.trigger_handler
async def login(request: Request):
    form = await get_form_data(request)
    if await authenticate(form["username"], form["password"]):
        return RedirectResponse("/dashboard", status_code=303)
    error_state.set("Invalid credentials")
```

## Handler naming

By default the trigger route name is derived from the function's `__name__`.
You can override it explicitly with `@ui.trigger_handler("custom_name")`:

```python
@ui.trigger_handler            # route: /_trigger/increment
def increment():
    ...

@ui.trigger_handler("inc")    # route: /_trigger/inc
def increment():
    ...
```

The component's `trigger` parameter takes the callable, so the name is
transparent to the component — it reads the URL from the function object
either way.
