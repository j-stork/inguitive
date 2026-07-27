"""Command-line interface for inguitive."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

console = Console()

STARTER_TEMPLATE = """from inguitive import create_app, Div, Text

app = create_app()


@app.page("/")
def home():
    return Div(
        Text("Welcome!"),
        css="w-full min-h-screen flex justify-center items-center",
    )
"""


def init_command(args):
    """Handle the init command - creates a new app.py file."""
    target_file = Path("app.py")

    if target_file.exists():
        console.print(f"Error: {target_file} already exists.", file=sys.stderr)
        console.print("Aborting to avoid overwriting existing file.", file=sys.stderr)
        sys.exit(1)

    target_file.write_text(STARTER_TEMPLATE)
    console.print(f"Created {target_file}")
    console.print("\nRun your app with '[bold]inguitive run[/bold]'")


def run_command(args):
    """Handle the run command - executes the app via uvicorn."""
    from inguitive import run_app

    target = args.module if args.module else "app:app"

    # Handle file path conversion
    if target.endswith(".py") and ":" not in target:
        module_name = target[:-3]  # Remove .py
        uvicorn_target = f"{module_name}:app"
    else:
        uvicorn_target = target

    # Map CLI args to run_app parameters
    host = args.host if hasattr(args, 'host') else '0.0.0.0'
    port = args.port if hasattr(args, 'port') else 8000
    reload = not args.no_reload

    try:
        run_app(
            app_module=uvicorn_target,
            host=host,
            port=port,
            reload=reload
        )
    except KeyboardInterrupt:
        pass
    except ImportError as e:
        if "uvicorn" in str(e):
            console.print("Error: uvicorn not found. Make sure uvicorn is installed.", file=sys.stderr)
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
