"""Command-line interface for inguitive."""

import argparse
import sys
from pathlib import Path

STARTER_TEMPLATE = '''from inguitive import Text, create_app

app = create_app()


@app.page("/")
def home():
    return Text("Welcome!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
'''


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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
