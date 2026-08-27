"""Utility functions for inguitive framework."""

import ast
import importlib.resources
from pathlib import Path

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


def _top_level_definitions(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef]:
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


def _kind_of(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
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
        output_lines.append(f"**Location:**\n\n`{py_file}`\n")

        tree = ast.parse(py_file.read_text())

        # Module docstring: the first top-level string-literal expression.
        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            rendered = _render_docstring(module_docstring)
            output_lines.append(f"**Description:**\n\n{rendered}\n")

        for node in _top_level_definitions(tree):
            name = f"`{node.name}` ({_kind_of(node)})"
            output_lines.append("---\n")
            output_lines.append(f"### {name}\n")
            output_lines.append(f"**Location:**\n\n`{py_file}:{node.lineno}-{node.end_lineno}`\n")

            docstring = ast.get_docstring(node)
            if docstring:
                rendered = _render_docstring(docstring)
                output_lines.append(f"**Description:**\n\n{rendered}\n")

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

    # List example applications as an index, not embedded source. The apps
    # ship inside the package (see [tool.setuptools.packages.find] in
    # pyproject.toml), so an LLM with file access can read any of them on
    # demand via the listed path. Embedding ~1500 lines of source would
    # bloat the index and crowd the context window with content the reader
    # may never need; a compact, descriptive map lets the reader decide
    # which file to open.
    examples_path = inguitive_src_path / "examples"
    if examples_path.is_dir():
        _append_examples_section(output_lines, examples_path)

    output_lines.append("\n")

    return "\n".join(output_lines)


def _example_docstring(path: Path) -> str:
    """Return the full module docstring for an example file.

    Returns an empty string when the file has no module docstring (e.g.
    ``svg.py``), so the caller can ``if docstring:``-guard the section.

    Args:
        path: Path to the example ``.py`` file.

    Returns:
        The complete, dedented module docstring, or "" if absent.
    """
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return ""
    return ast.get_docstring(tree) or ""


def _append_examples_section(output_lines: list[str], examples_path: Path) -> None:
    """Append the Example Applications section to ``output_lines`` in place.

    Emits one subsection per runnable example app, mirroring the structure
    used for classes and functions: a ``### `name``` heading, a
    ``**Location:**`` line with the on-disk path, a ``**Description:**``
    block with the file's complete module docstring, and a trailing
    ``---`` separator. Source is deliberately not embedded — the apps ship
    inside the package, so an LLM with file access reads them on demand via
    the listed path. A short intro records the shared support files
    (``css.py``, ``svg.py``) every app imports.

    Apps are ordered alphabetically for deterministic, diff-friendly output.

    Args:
        output_lines: The running list of Markdown lines to append to.
        examples_path: Path to the ``inguitive/examples/`` directory.
    """
    support_files = {"css.py", "svg.py"}
    all_files = sorted(p for p in examples_path.glob("*.py") if p.name != "__init__.py")
    apps = [p for p in all_files if p.name not in support_files]

    output_lines.append("---\n")
    output_lines.append("## Examples\n")
    output_lines.append(
        "Complete runnable apps shipped with the package, demonstrating how "
        "State, trigger handlers, components, forms, and SSE compose into a "
        "working application. Read any of them via the listed path when you "
        "need the full source. All apps import the shared scaffolds `css.py` "
        "and `svg.py` from the same directory (`inguitive init` writes these "
        "into a project).\n"
    )

    for path in apps:
        output_lines.append("---\n")
        output_lines.append(f"### `{path.name}`\n")
        output_lines.append(f"**Location:**\n\n`{path}`\n")
        docstring = _example_docstring(path)
        if docstring:
            rendered = _render_docstring(docstring)
            output_lines.append(f"**Description:**\n\n{rendered}\n")
