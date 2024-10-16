import importlib.util
import pkgutil
import sys
from pathlib import Path

from typer import Typer

import ragbits

app = Typer(no_args_is_help=True)


def main() -> None:
    """
    Main entry point for the CLI.

    This function registers all the CLI modules in the ragbits packages:
        - iterates over every package in the ragbits.* namespace
        - it looks for `cli` package / module
        - if found it imports the `register` function from the `cli` module and calls it with the `app` object
        - register function should add the CLI commands to the `app` object
    """
    help_only = len(sys.argv) == 1 or sys.argv[1] == "--help"

    cli_enabled_modules = [
        module
        for i, module in enumerate(pkgutil.iter_modules(ragbits.__path__))
        if module.ispkg and module.name != "cli" and (Path(ragbits.__path__[i]) / module.name / "cli.py").exists()
    ]
    for module in cli_enabled_modules:
        register_func = importlib.import_module(f"ragbits.{module.name}.cli").register
        register_func(app, help_only)

    app()
