# API Reference

Auto-generated from source docstrings. All public names are exported from
`inguitive` and can be imported directly:

```python
from inguitive import (
    # UI
    UI, SessionMiddleware,
    # Components
    Component, Div, Button, Label, Text, Header,
    Input, Textarea, Select, Checkbox, Radio, Form,
    Anchor, Image, Icon, DataTable, TemplateComponent,
    # State
    State, SessionState,
    # Trigger
    get_trigger_args, get_form_data,
    # Session
    SessionBackend, MemoryBackend,
    set_session_backend, get_session_backend,
    get_session_id, session_active, session_context,
    # HTMX helpers
    update_components, nl2br,
)
```

Redis-backed sessions are an optional extra:

```python
# pip install "inguitive[redis]"
from inguitive.backends.redis import RedisBackend
```

Use the navigation to browse individual modules.
