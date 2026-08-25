"""Command-line interface for inguitive."""

import argparse
import os
import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from inguitive.utils import gather_package_documentation

console = Console()
error_console = Console(file=sys.stderr)


def error_display(message: str, title: str = "Error"):
    """Display an error message in a styled panel."""
    panel = Panel(
        message,
        title="[bold]" + title + "[/bold]",
        title_align="left",
        border_style="red",
    )
    error_console.print(panel)


APP_CONTENT = """from markupsafe import Markup

from css import BRAND_COLORS
from inguitive import Div, Icon, Image, Link, Text, create_app
from svg import BOOK, GLOBE

app = create_app()


@app.page("/")
def home():
    return Div(
        Div(
            Text("WELCOME TO", css=f"tracking-widest text-{BRAND_COLORS['navy_500']}"),
            Image(src="/static/inguitive_logo_white_text.svg", alt="Inguitive", css="h-60 w-auto"),
            Text("Intuitive. Reactive. Pure-Python.", css="text-2xl text-white"),
            Div(
                Link(
                    Icon(GLOBE),
                    "Visit inguitive.com",
                    href="#",
                    css=f"inline-flex items-center gap-x-2 px-3 py-2 rounded-md font-medium cursor-pointer text-white bg-{BRAND_COLORS['blue_500']} hover:bg-{BRAND_COLORS['blue_400']} active:bg-{BRAND_COLORS['blue_500']}",
                ),
                Link(
                    Icon(BOOK),
                    "Read the docs",
                    href="#",
                    css="inline-flex items-center gap-x-2 px-3 py-2 rounded-md font-medium cursor-pointer text-white border border-white hover:bg-white/10 active:bg-transparent",
                ),
                css="flex gap-6",
            ),
            css=f"flex flex-col gap-6 justify-center items-center h-full p-6 rounded-xl bg-{BRAND_COLORS['navy_900']}",
        ),
        css=f"h-dvh p-3 bg-{BRAND_COLORS['navy_950']}"
    )

"""

CSS_CONTENT = """# Insert Tailwind CSS class constants here. The examples below show you how it works.

BRAND_COLORS = {
    "blue_400": "#3D6EF0",
    "blue_500": "#1147E8",
    "violet_600": "#CA00E0",
    "navy_500": "#4977C1",
    "navy_900": "#10182E",
    "navy_950": "#090E1B",
}

# Wrap the color values in square brackets for Tailwind CSS compatibility
for color_name, color_value in BRAND_COLORS.items():
    if "#" in color_value:
        BRAND_COLORS[color_name] = "[" + color_value.strip() + "]"

"""

SVG_CONTENT = '''# Insert SVG icon constants here. The examples below show you how it works.
# In app.py, you can use these icons like this:
#   from inguitive import Icon
#   from svg import ICON_NAME
#   Icon(ICON_NAME, css="w-6 h-6 text-gray-800 dark:text-white")

from markupsafe import Markup

GLOBE = Markup("""
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
</svg>
""")

BOOK = Markup("""
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
</svg>
""")

'''

def init_command(args):
    """Handle the init command - creates a new app.py file."""
    target_file = Path("app.py")

    if target_file.exists():
        error_display(
            "Aborting to avoid overwriting existing file.",
            title=f"{target_file} already exists",
        )
        sys.exit(1)

    target_file.write_text(APP_CONTENT)
    console.print(f"Created {target_file}")

    # Create css.py and svg.py files
    css_file = Path("css.py")
    svg_file = Path("svg.py")

    if not css_file.exists():
        css_file.write_text(CSS_CONTENT)
        console.print(f"Created {css_file}")

    if not svg_file.exists():
        svg_file.write_text(SVG_CONTENT)
        console.print(f"Created {svg_file}")

    # Copy the logo image
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    logo_src = Path(__file__).parent / "static" / "inguitive_logo_white_text.svg"
    logo_dst = static_dir / "inguitive_logo_white_text.svg"
    if logo_src.exists():
        shutil.copy(logo_src, logo_dst)
        console.print(f"Created {logo_dst}")

    # Ask if user wants to create llms-inguitive.md
    llms_file = Path("llms-inguitive.md")
    response = input("Create llms-inguitive.md for LLM indexing? [y/N]: ").lower()
    if response in ("y", "yes"):
        llms_content = gather_package_documentation()
        llms_file.write_text(llms_content)
        console.print(f"Created {llms_file}")

    console.print("\nRun your app with '[bold]inguitive run[/bold]'")


def run_command(args):
    """Handle the run command - executes the app via uvicorn."""
    from inguitive import run_app

    # Ensure the CWD is importable by uvicorn's reloader subprocess.
    # Mirrors what the uvicorn CLI does; also sets PYTHONPATH so that
    # subprocess spawned via multiprocessing 'spawn' (macOS, Windows)
    # inherits the path without relying on sys.path propagation.
    if "" not in sys.path:
        sys.path.insert(0, "")
    cwd = str(Path.cwd())
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if cwd not in existing_pythonpath.split(os.pathsep):
        os.environ["PYTHONPATH"] = (
            f"{cwd}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else cwd
        )

    target = args.module if args.module else "app:app"

    # Handle file path conversion
    if target.endswith(".py") and ":" not in target:
        module_name = target[:-3]  # Remove .py
        uvicorn_target = f"{module_name}:app"
    else:
        uvicorn_target = target

    # Map CLI args to run_app parameters
    host = args.host if hasattr(args, "host") else "0.0.0.0"
    port = args.port if hasattr(args, "port") else 8000
    reload = not args.no_reload

    try:
        run_app(
            app_module=uvicorn_target,
            host=host,
            port=port,
            reload=reload,
        )
    except KeyboardInterrupt:
        pass
    except ImportError as e:
        if "uvicorn" in str(e):
            error_display(
                "Make sure uvicorn is installed.",
                title="uvicorn not found",
            )
            sys.exit(1)
        raise


def main():
    """Main entry point for the inguitive CLI."""
    from inguitive import __version__

    parser = argparse.ArgumentParser(
        prog="inguitive",
        description="inguitive - A pure Python web framework",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser(
        "init",
        help="Create a new inguitive app in the current directory",
    )
    init_parser.set_defaults(func=init_command)

    run_parser = subparsers.add_parser(
        "run",
        help="Run the inguitive app using uvicorn",
    )
    run_parser.add_argument(
        "module",
        nargs="?",
        default=None,
        help="Module:instance to run (e.g., 'app:app' or 'myapp.py'). Defaults to 'app:app'",
    )
    run_parser.add_argument(
        "--no-reload",
        action="store_true",
        default=False,
        help="Disable auto-reload",
    )
    run_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    run_parser.set_defaults(func=run_command)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
