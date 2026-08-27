# Form Validation

inguitive provides a declarative form validation layer built around three
primitives: `FormSchema`, `field()`, and the `@validate_form` decorator.

## Quick example

```python
from inguitive import FormSchema, field, validate_form, RequiredValidator, MinLengthValidator

class RegistrationSchema(FormSchema):
    username = field(str, required=True, min_length=3, max_length=20)
    email    = field(str, required=True, regex=r"^[\w.-]+@[\w.-]+\.\w+$")
    password = field(
        str,
        validators=[
            RequiredValidator("Password is required"),
            MinLengthValidator(8, "Password must be at least 8 characters"),
        ],
    )
    age      = field(int, default=0, min_value=0, max_value=150)

@app.trigger_handler
@validate_form(RegistrationSchema)
async def register(form: RegistrationSchema) -> str:
    # form is fully validated and typed
    create_user(form.username, form.email, form.password, form.age)
    return redirect("/dashboard")
```

## `field()` — defining fields

```python
field(
    field_type,           # Python type: str, int, float, bool
    required=False,       # reject missing or empty values
    default=None,         # value used when field is absent and not required
    error_message=None,   # shared message for all built-in validators
    min_length=None,      # str: minimum length
    max_length=None,      # str: maximum length
    min_value=None,       # int/float: minimum value
    max_value=None,       # int/float: maximum value
    regex=None,           # str: pattern (full match via re.fullmatch)
    validators=None,      # list of Validator instances (see below)
    coerce=True,          # attempt type coercion from str
)
```

Type coercion converts incoming strings to the declared type automatically:
`"42"` becomes `42` for `field(int)`, `"true"` becomes `True` for
`field(bool)`.

## Built-in validators

| Validator | Parameters | Description |
|---|---|---|
| `RequiredValidator` | `message` | Field must be present and non-empty |
| `MinLengthValidator` | `min_length, message` | String minimum length |
| `MaxLengthValidator` | `max_length, message` | String maximum length |
| `MinValueValidator` | `min_value, message` | Numeric minimum |
| `MaxValueValidator` | `max_value, message` | Numeric maximum |
| `RegexValidator` | `pattern, message` | Full-string regex match |
| `CustomValidator` | `func, message` | Arbitrary validation function |

## `validators=[...]` — per-constraint messages

The shorthand parameters (`required`, `min_length`, etc.) share a single
`error_message`. To give each constraint its own message, use `validators=`:

```python
password = field(
    str,
    validators=[
        RequiredValidator("Password is required"),
        MinLengthValidator(8, "Must be at least 8 characters"),
        RegexValidator(r".*[A-Z].*", "Must contain an uppercase letter"),
    ],
)
```

## `CustomValidator`

Pass a callable that receives the field value and returns `True` for valid,
`False` for invalid:

```python
from inguitive import CustomValidator

def is_unique_username(value: str) -> bool:
    return not User.objects.filter(username=value).exists()

username = field(
    str,
    required=True,
    validators=[CustomValidator(is_unique_username, "Username is already taken")],
)
```

!!! note "Optional fields and `CustomValidator`"
    When a field has no `RequiredValidator` and is absent from the submitted
    data, `CustomValidator` is **not called** — the field is simply treated as
    optional and uses its default value. Your validator function does not need
    to handle `None`.

## Cross-field validation

Override `validate()` on the schema class to add rules that span multiple
fields. Raise `ValidationError` with a per-field error dict:

```python
from inguitive import FormSchema, field, ValidationError

class PasswordChangeSchema(FormSchema):
    new_password    = field(str, validators=[RequiredValidator("Required"), MinLengthValidator(8, "Too short")])
    confirm_password = field(str, required=True)

    def validate(self):
        super().validate()
        if self.new_password != self.confirm_password:
            raise ValidationError({"confirm_password": ["Passwords do not match"]})
```

## `@validate_form` — wiring to a trigger handler

```python
@app.trigger_handler
@validate_form(RegistrationSchema)
async def register(form: RegistrationSchema) -> str:
    ...
```

When validation fails, `validate_form` raises `ValidationError` by default.
To handle errors in the handler instead, pass `raise_on_invalid=False`:

```python
@app.trigger_handler
@validate_form(RegistrationSchema, raise_on_invalid=False)
async def register(form: RegistrationSchema, errors: dict) -> str:
    if errors:
        error_state.set(errors)
        return ""
    ...
```

## Accessing validated values

After `validate_form` injects the schema instance, access field values as
attributes:

```python
async def register(form: RegistrationSchema):
    print(form.username)   # str
    print(form.age)        # int — already coerced
    print(form.is_valid)   # True
    print(form.errors)     # {} (empty on success)
```

## Schema inheritance

`FormSchema` subclasses inherit all fields from their parents. Child fields
override parent fields with the same name. Multiple inheritance is resolved
in MRO order — later bases take lower priority than earlier ones:

```python
class BaseSchema(FormSchema):
    email = field(str, required=True, regex=r".*@.*")

class ProfileSchema(BaseSchema):
    name = field(str, required=True, min_length=1)
    bio  = field(str, default="")
    # also has: email (inherited)
```
