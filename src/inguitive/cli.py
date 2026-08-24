"""Command-line interface for inguitive."""

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

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


APP_CONTENT = """from css import BRAND_COLORS
from inguitive import Div, Icon, Link, Text, create_app
from svg import BOOK, GLOBE

app = create_app()


@app.page("/")
def home():
    return Div(
        Div(
            Text("Welcome to"),
            Text("inguitive", css="text-3xl font-bold"),
            Text("The modern web framework."),
            Text("Intuitive. Reactive. Pure-Python.", css="italic"),
            Div(
                Link(
                    Icon(GLOBE, css="w-5 h-5"),
                    "Go to inguitive.com",
                    href="#",
                    css="inline-flex items-center gap-x-2 px-3 py-2 bg-blue-500 rounded-md",
                ),
                Link(
                    Icon(BOOK, css="w-5 h-5"),
                    "Read the docs",
                    href="#",
                    css="inline-flex items-center gap-x-2 px-3 py-2 bg-blue-500 rounded-md",
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
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="512" height="512">
  <path d="M12,0A12,12,0,1,0,24,12,12.013,12.013,0,0,0,12,0Zm8.647,7H17.426a19.676,19.676,0,0,0-2.821-4.644A10.031,10.031,0,0,1,20.647,7ZM16.5,12a10.211,10.211,0,0,1-.476,3H7.976A10.211,10.211,0,0,1,7.5,12a10.211,10.211,0,0,1,.476-3h8.048A10.211,10.211,0,0,1,16.5,12ZM8.778,17h6.444A19.614,19.614,0,0,1,12,21.588,19.57,19.57,0,0,1,8.778,17Zm0-10A19.614,19.614,0,0,1,12,2.412,19.57,19.57,0,0,1,15.222,7ZM9.4,2.356A19.676,19.676,0,0,0,6.574,7H3.353A10.031,10.031,0,0,1,9.4,2.356ZM2.461,9H5.9a12.016,12.016,0,0,0-.4,3,12.016,12.016,0,0,0,.4,3H2.461a9.992,9.992,0,0,1,0-6Zm.892,8H6.574A19.676,19.676,0,0,0,9.4,21.644,10.031,10.031,0,0,1,3.353,17Zm11.252,4.644A19.676,19.676,0,0,0,17.426,17h3.221A10.031,10.031,0,0,1,14.605,21.644ZM21.539,15H18.1a12.016,12.016,0,0,0,.4-3,12.016,12.016,0,0,0-.4-3h3.437a9.992,9.992,0,0,1,0,6Z"/>
</svg>
""")

BOOK = Markup("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="512" height="512">
  <path d="M12,24c-.555,0-1.109-.077-1.648-.231l-6.726-1.921c-2.135-.61-3.626-2.587-3.626-4.808V4c0-.552,.448-1,1-1s1,.448,1,1v13.04c0,1.333,.895,2.519,2.176,2.885l6.726,1.921c.719,.205,1.478,.205,2.198,0l6.725-1.921c1.281-.366,2.176-1.552,2.176-2.885V3c0-.552,.448-1,1-1s1,.448,1,1v14.04c0,2.22-1.491,4.197-3.626,4.808l-6.726,1.921c-.54,.154-1.094,.231-1.648,.231ZM18.023,.155c-.728-.269-1.539-.202-2.26,.086l-.877,.35c-1.139,.455-1.887,1.559-1.887,2.786v14.496c-.328,.084-.663,.127-1,.127s-.672-.043-1-.127V3.377c0-1.227-.747-2.331-1.887-2.786l-.878-.351c-.721-.288-1.532-.355-2.26-.085-1.215,.45-1.976,1.583-1.976,2.822V15.691c0,1.339,.888,2.516,2.175,2.884l4.176,1.194c.538,.153,1.093,.23,1.648,.23s1.11-.077,1.648-.23l4.176-1.194c1.288-.368,2.175-1.545,2.175-2.884V2.977c0-1.239-.762-2.373-1.977-2.822Z"/>
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
