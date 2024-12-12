import importlib.util
import pkgutil
from pathlib import Path
from typing import Annotated

import typer

import ragbits

from .state import OutputType, cli_state, print_output

__all__ = [
    "OutputType",
    "app",
    "cli_state",
    "print_output",
]

app = typer.Typer(no_args_is_help=True)


@app.callback()
def output_type(
    # `OutputType.text.value` used as a workaround for the issue with `typer.Option` not accepting Enum values
    output: Annotated[
        OutputType, typer.Option("--output", "-o", help="Set the output type (text or json)")
    ] = OutputType.text.value,  # type: ignore
) -> None:
    """Sets an output type for the CLI
    Args:
        output: type of output to be set
    """
    cli_state.output_type = output


def autoregister() -> None:
    """
    Autodiscover and register all the CLI modules in the ragbits packages.

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


def main() -> None:
    """
    Main entry point for the CLI. Registers all the CLI commands and runs the app.
    """
    autoregister()
    app()
