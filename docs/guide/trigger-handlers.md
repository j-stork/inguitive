# Trigger Handlers

Trigger handlers are the server-side functions that respond to user interactions.
inguitive registers an HTMX POST endpoint for each one and returns out-of-band
HTML swaps for any components whose state changed.

## Basic handlers

```python
@app.trigger_handler
def save():
    # do something
    pass

@app.trigger_handler
async def fetch_data():
    result = await some_async_call()
    data_state.set(result)
```

Both sync and async functions are supported. Use `async def` whenever your
handler performs I/O (database queries, HTTP calls, file reads).

## Trigger arguments

Pass data from a component to its handler using `trigger_args` on the component
and `get_trigger_args()` inside the handler:

```python
from inguitive import get_trigger_args

@app.trigger_handler
def delete_item():
    item_id = get_trigger_args().get("id")
    items.set([i for i in items.get() if i["id"] != item_id])

# In a component:
Button(
    "Delete",
    trigger="delete_item",
    trigger_args={"id": item["id"]},
)
```

`trigger_args` are sent as URL query parameters. `get_trigger_args()` returns
them as `dict[str, str]` — all values are strings, so cast as needed.

## Form data

When a trigger is fired from inside a `<form>`, inguitive collects the submitted
form data and makes it available as a `form_data: dict[str, str]` parameter.
Declare it in the handler signature to receive it:

```python
@app.trigger_handler
def submit_contact(form_data: dict):
    name  = form_data.get("name", "")
    email = form_data.get("email", "")
    # process...
```

For validated form data, use the `validate_form` decorator instead —
see [Form Validation](form-validation.md).

## Returning HTML

Trigger handlers can return an HTML string that inguitive injects into the page.
This is useful for flash messages, confirmation banners, or any content that is
not tied to a listening component:

```python
@app.trigger_handler
def submit():
    # ... process ...
    return '<p class="text-green-600">Saved successfully!</p>'
```

The returned HTML is appended to the HTMX response alongside any OOB swaps.

## Redirecting

Use `redirect()` to send the user to a different page after a handler runs:

```python
from inguitive import redirect

@app.trigger_handler
async def login(form_data: dict):
    if await authenticate(form_data["username"], form_data["password"]):
        return redirect("/dashboard")
    error_state.set("Invalid credentials")
```

## Handler naming

The name used in `trigger="..."` on a component must exactly match the function
name of the handler:

```python
@app.trigger_handler
def increment():       # trigger="increment"
    ...
```

inguitive uses the function's `__name__` attribute for routing, so renaming
with `functools.wraps` or similar tools is transparent.
