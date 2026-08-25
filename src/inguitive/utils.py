"""Utility functions for inguitive framework."""

import importlib.resources


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

        >>> nl2br("Line 1\r\nLine 2")
        'Line 1<br>Line 2'

        >>> nl2br(None)
        ''
    """
    if text is None:
        return ""
    return text.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")


def _extract_docstring(content: list[str], start_index: int) -> tuple[str, int]:
    """Extract a docstring starting at start_index from file content.

    Returns:
        Tuple of (docstring_text, end_index) where end_index is the line after the closing quote.
        Returns ("", start_index) if no docstring is found.
    """
    if start_index >= len(content):
        return "", start_index

    line = content[start_index]
    stripped_line = line.strip()

    # Check for both triple-quote styles
    if stripped_line.startswith('"""'):
        quote = '"""'
    elif stripped_line.startswith("'''"):
        quote = "'''"
    else:
        return "", start_index

    # Check if it's a single-line docstring
    if stripped_line.endswith(quote):
        # Extract content between quotes
        docstring = stripped_line[len(quote) : -len(quote)].strip()
        return docstring, start_index + 1

    # Multi-line docstring - collect until closing quote
    docstring_lines = []

    # Extract first line (after opening quote)
    first_line = stripped_line[len(quote) :].strip()
    if first_line:
        docstring_lines.append(first_line)

    end_index = start_index + 1

    while end_index < len(content):
        if quote in content[end_index]:
            # Extract content from this line (before the closing quote)
            closing_line = content[end_index]
            quote_pos = closing_line.find(quote)
            if quote_pos > 0:
                docstring_lines.append(closing_line[:quote_pos].rstrip())
            break
        docstring_lines.append(content[end_index].rstrip())
        end_index += 1

    docstring = "\n".join(docstring_lines).strip()
    return docstring, end_index + 1


def _get_top_level_defs(content: list[str]) -> list[tuple[int, int, str]]:
    """Get all top-level class and function definitions.

    Returns list of tuples: (start_line, end_line, name)
    """
    definitions = []
    i = 0

    while i < len(content):
        line = content[i]

        # Only consider top-level (not indented)
        if not line.startswith(" ") and not line.startswith("\t") and line.strip():
            if line.startswith("class ") or line.startswith("def "):
                # Extract name
                name_part = line.strip()
                if line.startswith("class "):
                    name = name_part[len("class ") :].split("(")[0].split(":")[0].strip()
                else:
                    name = name_part[len("def ") :].split("(")[0].split(":")[0].strip()

                # Find end of this definition
                j = i + 1

                while j < len(content):
                    next_line = content[j]
                    next_stripped = next_line.strip()

                    # Check if we've hit another top-level definition
                    if next_line and not next_line.startswith(" ") and not next_line.startswith("\t"):
                        if next_stripped.startswith("class ") or next_stripped.startswith("def "):
                            break
                    j += 1

                definitions.append((i, j - 1, name))
                i = j - 1  # Skip to end of definition

        i += 1

    return definitions


def gather_package_documentation() -> str:
    """Gather package documentation including classes, functions, and templates.

    Returns a Markdown string listing all classes and functions with their
    line ranges and docstrings, plus template files with their paths.
    """
    from pathlib import Path

    inguitive_src_path = Path(str(importlib.resources.files("inguitive")))

    # List all Python files in the inguitive package directory
    python_files = [f for f in inguitive_src_path.iterdir() if f.suffix == ".py"]

    output_lines = []

    # Add Python files with their classes and functions
    for py_file in python_files:
        output_lines.append("---\n")
        output_lines.append(f"## {py_file.name}\n")
        output_lines.append(f"*Location: {py_file}*\n")

        with open(py_file) as f:
            content = f.readlines()

        # Get all top-level definitions
        definitions = _get_top_level_defs(content)

        for start, end, name in definitions:
            output_lines.append(f"### {name}\n")
            output_lines.append(f"*Defined at lines {start + 1}-{end}*\n")

            # Extract docstring for classes and functions
            # Look for docstring immediately after definition
            docstring_start = start + 1

            # Skip empty lines
            while docstring_start <= end and content[docstring_start].strip() == "":
                docstring_start += 1

            # Check if we're at a docstring
            if docstring_start <= end:
                stripped = content[docstring_start].strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    docstring, _ = _extract_docstring(content, docstring_start)
                    if docstring:
                        output_lines.append(f"**Docstring:**\n\n{docstring}\n")

    # Add template files
    templates_path = inguitive_src_path / "templates"
    if templates_path.exists():
        template_files = [f for f in templates_path.iterdir() if f.is_file()]
        if template_files:
            output_lines.append("---\n")
            output_lines.append("## Templates\n")
            for template_file in template_files:
                output_lines.append(f"### {template_file.name}\n")
                output_lines.append(f"*Location: {template_file}*\n")

    return "\n".join(output_lines)
