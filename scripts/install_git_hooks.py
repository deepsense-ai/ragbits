# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "inquirer",
#     "rich",
# ]
# ///
# To run this script and install git hooks, run the following command:
#
#   uv run scripts/install_git_hooks.py
#
from pathlib import Path

from inquirer.shortcuts import list_input
from rich import print as pprint

HOOK_BODY = """
#!/usr/bin/env bash

echo "🧹 Running formatting...\n"
uv run ruff format --check

if [ $? -ne 0 ]
then
    echo "⚠ Formatting failed. Running autofix & aborting..."
    uv run ruff format
    exit 1
fi

echo "✅ Formatting passed!"
echo "\n📜 Running linting...\n"

uv run ruff check

if [ $? -ne 0 ]
then
    echo "⚠ Linting failed. Aborting..."
    exit 1
fi

echo "✅ Linting passed!"

echo "\n📚 Making sure that docs build...\n"

uv run mkdocs build --strict

if [ $? -ne 0 ]
then
    echo "⚠ Docs build failed. Aborting..."
    exit 1
fi

echo "\n🔎 Running type checking...\n"

uv run mypy .

if [ $? -ne 0 ]
then
    echo "⚠ Type checking failed. Aborting..."
    exit 1
fi

echo "✅ Type checking passed!"
"""


def main() -> None:
    """
    Install pre-commit or pre-push git hooks.
    """
    hooks_dir = Path(__file__).parent.parent / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_type = list_input("Select a hook to install", choices=["pre-commit", "pre-push"])

    (hooks_dir / "pre-commit").unlink(missing_ok=True)
    (hooks_dir / "pre-push").unlink(missing_ok=True)

    pre_commit_hook = hooks_dir / hook_type
    pre_commit_hook.write_text(HOOK_BODY, encoding="utf-8")
    pre_commit_hook.chmod(0o755)

    pprint(f"[cyan]Git hook for [b]{hook_type}[/b] installed!")


if __name__ == "__main__":
    main()
