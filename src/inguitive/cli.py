"""Command-line interface for inguitive."""

import argparse
import subprocess
import sys
from pathlib import Path

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
        print(f"Error: {target_file} already exists.", file=sys.stderr)
        print("Aborting to avoid overwriting existing file.", file=sys.stderr)
        sys.exit(1)

    target_file.write_text(STARTER_TEMPLATE)
    print(f"Created {target_file}")
    print("\nTo run your app:")
    print("  uvicorn app:app --reload")


def run_command(args):
    """Handle the run command - executes the app via uvicorn."""
    target = args.module if args.module else "app:app"

    # Handle file path conversion
    if target.endswith(".py") and ":" not in target:
        module_name = target[:-3]  # Remove .py
        uvicorn_target = f"{module_name}:app"
    else:
        uvicorn_target = target

    # Build command
    cmd = ["uvicorn", uvicorn_target]
    if not args.no_reload:
        cmd.append("--reload")

    # Execute with same stdout/stderr
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("Error: uvicorn not found. Make sure uvicorn is installed.", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the inguitive CLI."""
    parser = argparse.ArgumentParser(
        prog="inguitive",
        description="inguitive - A pure Python web framework",
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
    run_parser.set_defaults(func=run_command)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
