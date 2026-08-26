"""Utility functions for inguitive framework."""

import ast
import importlib.resources
from pathlib import Path


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


def _render_docstring(docstring: str | None) -> str:
    """Render a docstring as a fenced Markdown code block.

    Returns an empty string when there is no docstring, so the caller can
    ``if rendered:``-guard the output section. Keeping the fencing decision
    in this single helper means the rendering style can be changed in one
    place without touching the parser.

    Args:
        docstring: Raw docstring text (typically from ``ast.get_docstring``,
            which already dedents and trims it). May be None or empty.

    Returns:
        The docstring wrapped in a ``` ``` ``` fence, or "" if empty.
    """
    if not docstring:
        return ""
    return "```\n" + docstring.strip() + "\n```"


def _top_level_definitions(tree: ast.Module) -> list[ast.AST]:
    """Return public top-level class and function definitions of ``tree``.

    "Public" means the name does not start with an underscore, matching the
    previous behaviour of skipping internal helpers. Both ``def`` and
    ``async def`` are included (the old line-based scanner silently dropped
    ``async def``). Decorators are not part of the returned nodes' line
    ranges; ``node.lineno`` points at the ``def``/``class`` keyword.

    Args:
        tree: A parsed module AST (``ast.parse(source)``).

    Returns:
        List of ``ast.FunctionDef``, ``ast.AsyncFunctionDef``, and
        ``ast.ClassDef`` nodes in source order.
    """
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]


def _kind_of(node: ast.AST) -> str:
    """Return the display kind for a definition node: 'class' or 'function'."""
    return "class" if isinstance(node, ast.ClassDef) else "function"


def gather_package_documentation() -> str:
    """Gather package documentation including classes, functions, and templates.

    Walks every ``.py`` file in the installed ``inguitive`` package, and for
    each one emits its module docstring plus a section per public top-level
    class/function with its line range and docstring. Template files are
    listed at the end. The result is a Markdown string suitable for an
    ``llms-inguitive.md`` index file.

    Parsing relies on the stdlib ``ast`` module rather than a hand-rolled
    line scanner, so names, exact line ranges (``end_lineno``), and real
    docstrings (``ast.get_docstring``) come straight from the syntax tree.

    Returns:
        Markdown documentation string.
    """
    inguitive_src_path = Path(str(importlib.resources.files("inguitive")))

    output_lines = ["# inguitive Package Documentation\n"]

    # Sort for deterministic, diff-friendly output regardless of filesystem
    # iteration order.
    for py_file in sorted(inguitive_src_path.glob("*.py")):
        output_lines.append("---\n")
        output_lines.append(f"## `{py_file.name}`\n")
        output_lines.append(f"**Module Location:**\n\n`{py_file}`\n")

        tree = ast.parse(py_file.read_text())

        # Module docstring: the first top-level string-literal expression.
        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            rendered = _render_docstring(module_docstring)
            output_lines.append(f"**Module Docstring:**\n\n{rendered}\n")

        for node in _top_level_definitions(tree):
            name = f"`{node.name}` ({_kind_of(node)})"
            output_lines.append("---\n")
            output_lines.append(f"### {name}\n")
            output_lines.append(f"**Location:**\n\n`{py_file}:{node.lineno}-{node.end_lineno}`\n")

            docstring = ast.get_docstring(node)
            if docstring:
                rendered = _render_docstring(docstring)
                output_lines.append(f"**Docstring:**\n\n{rendered}\n")

    # List template files if the package ships a templates directory.
    templates_path = inguitive_src_path / "templates"
    if templates_path.exists():
        template_files = sorted(
            f for f in templates_path.iterdir() if f.is_file()
        )
        if template_files:
            output_lines.append("---\n")
            output_lines.append("## Templates\n")
            for template_file in template_files:
                output_lines.append(f"### `{template_file.name}`\n")
                output_lines.append(f"**Location:**\n\n`{template_file}`\n")

    # Embed complete example applications. These ship inside the package
    # (see [tool.setuptools.packages.find] in pyproject.toml) so the docs are
    # available regardless of whether inguitive was pip-installed or run from
    # a source checkout. Full apps show how State, trigger handlers,
    # components, and SSE compose — context that a per-symbol API reference
    # cannot convey and that an LLM in a vibe-coding context benefits from.
    examples_path = inguitive_src_path / "examples"
    if examples_path.is_dir():
        _append_examples_section(output_lines, examples_path)

    output_lines.append("\n")

    return "\n".join(output_lines)


def _example_description(path: Path) -> str:
    """Return a one-line description for an example file, from its module docstring.

    Falls back to the filename when the file has no module docstring (e.g.
    ``svg.py``). Keeps the section readable when listed in a flat index.

    Args:
        path: Path to the example ``.py`` file.

    Returns:
        First non-empty line of the module docstring, or the file's stem.
    """
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return path.stem
    docstring = ast.get_docstring(tree)
    if not docstring:
        return path.stem
    first_line = docstring.strip().splitlines()[0]
    return first_line or path.stem


def _append_examples_section(output_lines: list[str], examples_path: Path) -> None:
    """Append the Example Applications section to ``output_lines`` in place.

    The section has two parts:

    1. *Support files* — ``css.py`` and ``svg.py``, the small scaffolds that
       ``inguitive init`` writes to the user's CWD and that every example app
       imports. Including them once here means the app sources below are
       self-explanatory (the reader can see what ``BRAND_COLORS`` or ``GLOBE``
       refer to).
    2. *Applications* — each runnable example app with its full source in a
       fenced code block, ordered alphabetically for deterministic output.

    Args:
        output_lines: The running list of Markdown lines to append to.
        examples_path: Path to the ``inguitive/examples/`` directory.
    """
    output_lines.append("---\n")
    output_lines.append("## Example Applications\n")
    output_lines.append(
        "Complete runnable apps shipped with the package. They demonstrate "
        "how State, trigger handlers, components, forms, and SSE compose "
        "into a working application.\n"
    )

    # Split support files from real apps. Support files are the scaffolds
    # every app imports; apps are everything else except the package marker.
    support_files = ["css.py", "svg.py"]
    all_files = sorted(p for p in examples_path.glob("*.py") if p.name != "__init__.py")
    apps = [p for p in all_files if p.name not in support_files]

    # Support files first, so the app sources below them are self-contained.
    output_lines.append("---\n")
    output_lines.append("### Support files\n")
    output_lines.append(
        "These are the scaffolds `inguitive init` creates in the project "
        "directory and that the example apps import.\n"
    )
    for name in support_files:
        path = examples_path / name
        if path.is_file():
            _append_example_file(output_lines, path, header_level=4)

    # Then the apps themselves.
    for path in apps:
        _append_example_file(output_lines, path, header_level=3)


def _append_example_file(
    output_lines: list[str], path: Path, header_level: int
) -> None:
    """Append one example file's header, description, and fenced source.

    Args:
        output_lines: The running list of Markdown lines to append to.
        path: Path to the example ``.py`` file.
        header_level: Markdown header level for the file's heading (e.g. 3
            for apps, 4 for support files nested under a subsection).
    """
    header = "#" * header_level
    output_lines.append(f"{header} `{path.name}`\n")
    output_lines.append(f"{_example_description(path)}\n")
    output_lines.append(f"*Location:* `{path}`\n")
    output_lines.append(f"```python\n{path.read_text()}```\n")
