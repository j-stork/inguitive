"""Tests for utility functions."""

from inguitive import nl2br


def test_nl2br_basic():
    """Test basic newline to <br> conversion."""
    assert nl2br("Line 1\nLine 2") == "Line 1<br>Line 2"


def test_nl2br_multiple_newlines():
    """Test multiple consecutive newlines."""
    assert nl2br("Line 1\n\n\nLine 2") == "Line 1<br><br><br>Line 2"


def test_nl2br_empty_string():
    """Test empty string handling."""
    assert nl2br("") == ""


def test_nl2br_no_newlines():
    """Test string without newlines remains unchanged."""
    assert nl2br("Single line") == "Single line"


def test_nl2br_none_input():
    """Test None input returns empty string."""
    assert nl2br(None) == ""


def test_nl2br_mixed_content():
    """Test newlines mixed with other content."""
    assert nl2br("Start\nMiddle\nEnd") == "Start<br>Middle<br>End"


def test_nl2br_preserves_other_whitespace():
    """Test that spaces and tabs are preserved."""
    assert nl2br("Line 1  \n\tLine 2") == "Line 1  <br>\tLine 2"


def test_nl2br_html_safe():
    """Test with existing HTML content."""
    # Note: This doesn't escape existing HTML - user's responsibility
    assert nl2br("<b>Bold\nNormal</b>") == "<b>Bold<br>Normal</b>"
