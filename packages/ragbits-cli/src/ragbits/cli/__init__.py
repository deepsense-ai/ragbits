import importlib.util
import pkgutil
from pathlib import Path

import typer

import ragbits

from .app import CLI

app = CLI(no_args_is_help=True)


@app.callback()
def output_type(
    output: str = typer.Option("text", "--output", "-o", help="Set the output type (text or json)"),
) -> None:
    """Sets an output type for the CLI
    Args:
        output: type of output to be set
    """
    app.set_output_type(output_type=output)
    print(f"Output type set to {output}")


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
        if module.ispkg and module.name != "cli" and (Path(module.module_finder.path) / module.name / "cli.py").exists()  # type: ignore
    ]

    for module in cli_enabled_modules:
        register_func = importlib.import_module(f"ragbits.{module.name}.cli").register
        register_func(app)

    app()
