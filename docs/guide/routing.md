# Routing and URL Parameters

Routing is FastAPI's job. Pages are plain `@app.get(...)` routes that return
`ui.page(...)`. There is no custom path-parameter conversion engine — you use
FastAPI's native `{name}` syntax and type annotations directly.

## Basic routing

```python
from fastapi import FastAPI
from inguitive import UI, Div, Text

app = FastAPI()
ui = UI(app)

@app.get("/")
def home():
    return ui.page(Div(Text("Home Page")))

@app.get("/about")
def about():
    return ui.page(Div(Text("About Us")))
```

Each `@app.get` registers a GET route. The handler returns `ui.page(component)`,
which wraps the component in the full HTML document shell.

## URL path parameters

Use FastAPI's `{name}` syntax to define dynamic segments. The handler's type
annotation tells FastAPI how to parse and validate the segment:

```python
@app.get("/user/{username}")
def user_profile(username: str):
    return ui.page(Div(Text(f"Hello, {username}")))
```

When a user visits `/user/john`, `username` receives the value `"john"`.

## Type annotations

| Type | Example | Description |
|------|---------|-------------|
| `str` | `/user/{name}` | String (default when no type is given) |
| `int` | `/post/{id}` | Integer, validates and converts |
| `float` | `/price/{amount}` | Floating point number |
| `path` | `/files/{subpath:path}` | Preserves slashes in the path |
| `uuid` | `/user/{user_id}` | UUID validation and conversion |

### Type validation

If a URL segment doesn't match the expected type, FastAPI returns an HTTP 422
error automatically — no handler-level validation code needed:

```python
@app.get("/post/{post_id}")
def show_post(post_id: int):
    return ui.page(Div(Text(f"Post {post_id}")))

# /post/42    -> OK, post_id = 42 (int)
# /post/abc   -> 422 Unprocessable Entity
```

### Path type

Use `path` when you need to capture URL segments that contain slashes:

```python
@app.get("/files/{subpath:path}")
def show_file(subpath: str):
    return ui.page(Div(Text(f"File: {subpath}")))

# /files/a/b/c.txt  -> subpath = "a/b/c.txt"
```

### UUID type

```python
import uuid

@app.get("/user/{user_id}")
def show_user(user_id: uuid.UUID):
    return ui.page(Div(Text(f"User: {user_id}")))

# /user/550e8400-e29b-41d4-a716-446655440000  -> OK
# /user/not-a-uuid                           -> 422
```

## Multiple parameters

You can use multiple path parameters in a single route and mix types:

```python
@app.get("/user/{user_id}/post/{post_id}")
def show_user_post(user_id: int, post_id: int):
    return ui.page(Div(Text(f"User {user_id}, Post {post_id}")))

# /user/123/post/456  -> user_id = 123, post_id = 456

@app.get("/category/{category}/page/{page}")
def show_category_page(category: str, page: int):
    return ui.page(Div(Text(f"{category} page {page}")))

# /category/books/page/5  -> category = "books", page = 5
```

## Navigation between pages

Use `Anchor` for traditional navigation (the URL changes, the page is
bookmarkable, the user can open in a new tab):

```python
from inguitive import Anchor

@app.get("/")
def home():
    return ui.page(
        Div(
            Anchor("About", href="/about", css="text-blue-600 hover:underline"),
        ),
    )
```

Use `RedirectResponse` for server-side redirects (e.g. redirecting the root
path to a default page):

```python
from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse("/page1", status_code=302)
```

`Anchor` vs `trigger`: `Anchor` performs a full page navigation (the URL
changes); `trigger` fires an HTMX POST that updates components in place (the
URL stays the same). See the [Components](components.md#navigation) guide for
the full comparison.

## Request and dependencies

Since pages are plain FastAPI routes, all FastAPI features are available
directly: `Request`, `Form(...)`, dependencies, query parameters, and more.

```python
from fastapi import Request

@app.get("/search")
def search(request: Request):
    q = request.query_params.get("q", "")
    return ui.page(Div(Text(f"Searching for: {q}")))
```

## Complete example

```python
from fastapi import FastAPI
from inguitive import UI, Div, Text

app = FastAPI()
ui = UI(app, title="User Profiles")

@app.get("/user/{username}")
def user_profile(username: str):
    return ui.page(Div(Text(f"Profile: {username}")))

@app.get("/user/{username}/post/{post_id}")
def user_post(username: str, post_id: int):
    return ui.page(Div(Text(f"{username}'s post #{post_id}")))

@app.get("/settings/{section}/{page}")
def settings_page(section: str, page: int):
    return ui.page(Div(Text(f"{section} settings, page {page}")))
```
