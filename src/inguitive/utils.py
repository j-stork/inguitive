"""Utility functions for inguitive framework."""

import markupsafe


def nl2br(text: str | None) -> markupsafe.Markup:
    """Convert newline characters to HTML line break tags, safely.

    Escapes HTML-special characters first (via ``markupsafe.escape``), then
    converts newline characters (``\\r\\n``, ``\\r``, ``\\n``) to ``<br>``
    tags, then returns a ``markupsafe.Markup`` so the framework emits the
    result as HTML rather than re-escaping the ``<br>`` tags it just
    produced.

    This is safe to call on untrusted user input: ``<script>`` becomes
    ``&lt;script&gt;`` (no script executes), and only newlines become
    ``<br>`` tags. Callers no longer need to wrap the input in
    ``Markup(nl2br(str(escape(content))))`` — ``nl2br(content)`` is enough.

    Args:
        text: Input string potentially containing newline characters.
        May be None, which returns an empty ``Markup``.

    Returns:
        A ``markupsafe.Markup`` with HTML-special characters escaped and
        newline characters replaced by ``<br>`` tags. None input returns
        an empty ``Markup``.

    Example:
        >>> nl2br("Line 1\\nLine 2")
        Markup('Line 1<br>Line 2')

        >>> nl2br("Hello\\n\\nWorld")
        Markup('Hello<br><br>World')

        >>> nl2br("Line 1\\r\\nLine 2")
        Markup('Line 1<br>Line 2')

        >>> nl2br(None)
        Markup('')

        >>> str(nl2br("<script>\\nalert(1)"))
        '&lt;script&gt;<br>alert(1)'
    """
    if text is None:
        return markupsafe.Markup("")
    # str() around escape(): markupsafe.escape returns a Markup object whose
    # .replace() re-escapes inserted substrings, so convert to plain str first
    # to keep the <br> replacement literal.
    escaped = str(markupsafe.escape(text))
    return markupsafe.Markup(
        escaped.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")
    )
