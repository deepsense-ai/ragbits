import importlib.util
import pkgutil

from typer import Typer

import ragbits

app = Typer()


def main() -> None:
    """
    Main entry point for the CLI.

    This function registers all the CLI modules in the ragbits packages:
        - iterates over every package in the ragbits.* namespace
        - it looks for `cli` package / module
        - if found it imports the `register` function from the `cli` module and calls it with the `app` object
        - register function should add the CLI commands to the `app` object
    """

    cli_enabled_modules = [
        module
        for module in pkgutil.iter_modules(ragbits.__path__)
        if module.ispkg and module.name != "cli" and importlib.util.find_spec(f"ragbits.{module.name}.cli")
    ]
    for module in cli_enabled_modules:
        register_func = importlib.import_module(f"ragbits.{module.name}.cli").register
        register_func(app)

    app()
