# Routing and URL Parameters

## Basic Routing

Pages are defined with the `@app.page` decorator:

```python
@app.page("/")
def index():
    return Div(Text("Home Page"))

@app.page("/about")
def about():
    return Div(Text("About Us"))
```

Each `@app.page` registers a GET route on your FastAPI application.

## URL Path Parameters

You can define dynamic URL segments using the `<name:type>` syntax:

```python
@app.page("/user/<username>")
def user_profile(username: str):
    return Div(Text(f"Hello, {username}"))
```

When a user visits `/user/john`, the `username` parameter will receive the value `"john"`.

### Type Annotations

The type in `<name:type>` specifies how the URL segment should be parsed:

| Type | Example | Description |
|------|---------|-------------|
| `str` | `/user/<name:str>` | String (default if no type specified) |
| `int` | `/post/<id:int>` | Integer, validates and converts |
| `float` | `/price/<amount:float>` | Floating point number |
| `bool` | `/toggle/<state:bool>` | Boolean (accepts: true, false, 1, 0, yes, no, on, off) |
| `path` | `/files/<subpath:path>` | Preserves slashes in the path |
| `uuid` | `/user/<id:uuid>` | UUID validation and conversion |

### Type Validation

If a URL segment doesn't match the expected type, inguitive returns an HTTP 400 error:

```python
@app.page("/post/<post_id:int>")
def show_post(post_id: int):
    return Div(Text(f"Post {post_id}"))

# /post/42    -> OK, post_id = 42 (int)
# /post/abc   -> 400 Bad Request with detail: "Invalid post_id: invalid literal for int()"
```

### Boolean Values

The `bool` type accepts these values (case-insensitive):

- **True**: `true`, `1`, `yes`, `on`
- **False**: `false`, `0`, `no`, `off`, or any other value

```python
@app.page("/toggle/<state:bool>")
def toggle(state: bool):
    return Div(Text(f"State: {state}"))

# /toggle/true   -> state = True
# /toggle/false  -> state = False
# /toggle/1      -> state = True
# /toggle/yes    -> state = True
```

### Path Type

Use `path` when you need to capture URL segments that contain slashes:

```python
@app.page("/files/<filepath:path>")
def show_file(filepath: str):
    return Div(Text(f"File: {filepath}"))

# /files/a/b/c.txt  -> filepath = "a/b/c.txt"
```

### UUID Type

The `uuid` type validates and converts to a UUID object:

```python
import uuid

@app.page("/user/<user_id:uuid>")
def show_user(user_id: uuid.UUID):
    return Div(Text(f"User: {user_id}"))

# /user/550e8400-e29b-41d4-a716-446655440000  -> OK
# /user/not-a-uuid                           -> 400 Bad Request
```

## Multiple Parameters

You can use multiple path parameters in a single route:

```python
@app.page("/user/<user_id:int>/post/<post_id:int>")
def show_user_post(user_id: int, post_id: int):
    return Div(Text(f"User {user_id}, Post {post_id}"))

# /user/123/post/456  -> user_id = 123, post_id = 456
```

You can also mix types:

```python
@app.page("/category/<category:str>/page/<page:int>")
def show_category_page(category: str, page: int):
    return Div(Text(f"{category} page {page}"))

# /category/books/page/5  -> category = "books", page = 5
```

## Default Type

If you omit the type, it defaults to `str`:

```python
@app.page("/user/<username>")
def user_profile(username: str):
    return Div(Text(f"Hello, {username}"))

# Equivalent to: /user/<username:str>
```

## Unknown Types

If you specify an unknown type name, it will be treated as `str`:

```python
@app.page("/test/<value:custom_type>")
def test_page(value: str):
    return Div(Text(f"Value: {value}"))

# value will be a string regardless of the unknown type annotation
```

## Accessing Request and Form Data

Path parameters work alongside the `request` and `form_data` parameters:

```python
@app.page("/user/<user_id:int>")
def user_profile(user_id: int, request):
    return Div(Text(f"User {user_id}, Method: {request.method}"))

@app.page("/user/<user_id:int>")
def user_profile(user_id: int, form_data: dict):
    return Div(Text(f"User {user_id}, Form: {form_data}"))
```

## Reserved Parameter Names

The names `request` and `form_data` are reserved for FastAPI request injection and **cannot** be used as path parameter names:

```python
# This will raise ValueError during app initialization:
@app.page("/test/<request:str>")
def test_page(request: str):
    return Div(Text(f"Param: {request}"))

# Error: Path parameter name 'request' is reserved and cannot be used.
```

## Parameter Precedence

When a path parameter has the same name as a function parameter that would normally receive `request` or `form_data`, the path parameter takes precedence. However, since `request` and `form_data` are reserved names, this situation cannot occur with those specific names.

## Root Path with Parameters

You can use parameters in the root path:

```python
@app.page("/<page_name:str>")
def dynamic_page(page_name: str):
    return Div(Text(f"Dynamic page: {page_name}"))

# /home      -> page_name = "home"
# /about     -> page_name = "about"
```

## Complete Example

```python
from inguitive import Div, Text, create_app

app = create_app(title="User Profiles")

@app.page("/user/<username:str>")
def user_profile(username: str):
    return Div(Text(f"Profile: {username}"))

@app.page("/user/<username:str>/post/<post_id:int>")
def user_post(username: str, post_id: int):
    return Div(Text(f"{username}'s post #{post_id}"))

@app.page("/settings/<section:str>/<page:int>")
def settings_page(section: str, page: int):
    return Div(Text(f"{section} settings, page {page}"))
```
