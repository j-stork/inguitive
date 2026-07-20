"""Utility functions for INGUITIVE framework."""


def nl2br(text: str | None) -> str:
    """Convert newline characters to HTML line break tags.

    Args:
        text: Input string potentially containing newline characters.
        May be None, which returns an empty string.

    Returns:
        String with all newline characters replaced by <br> tags.
        None input returns empty string.

    Example:
        >>> nl2br("Line 1\nLine 2")
        'Line 1<br>Line 2'

        >>> nl2br("Hello\n\nWorld")
        'Hello<br><br>World'

        >>> nl2br(None)
        ''
    """
    if text is None:
        return ""
    return text.replace("\n", "<br>")
