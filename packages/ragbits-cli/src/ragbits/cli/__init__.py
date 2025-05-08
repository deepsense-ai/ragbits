import importlib.util
import os
import pkgutil
from pathlib import Path
from typing import Annotated

# litellm downloads cost map on import, which creates extra latency in CLI.
# This config disables it.
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import click
import typer
from typer.main import get_command

import ragbits
from ragbits.core.audit.traces import set_trace_handlers

from .state import OutputType, cli_state, print_output

__all__ = [
    "OutputType",
    "app",
    "cli_state",
    "print_output",
]

app = typer.Typer(no_args_is_help=True)
_click_app: click.Command | None = None  # initialized in the `init_for_mkdocs` function


@app.callback()
def ragbits_cli(
    # `OutputType.text.value` used as a workaround for the issue with `typer.Option` not accepting Enum values
    output: Annotated[
        OutputType, typer.Option("--output", "-o", help="Set the output type (text or json)")
    ] = OutputType.text.value,  # type: ignore
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print additional information"),
) -> None:
    """Common CLI arguments for all ragbits commands."""
    cli_state.output_type = output
    cli_state.verbose = verbose

    if verbose == 1:
        typer.echo("Verbose mode is enabled.")
        set_trace_handlers("cli")


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


def _init_for_mkdocs() -> None:
    """
    Initializes the CLI app for the mkdocs environment.

    This function registers all the CLI commands and sets the `_click_app` variable to a click
    command object containing all the CLI commands. This way the `mkdocs-click` plugin can
    create an automatic CLI documentation.
    """
    global _click_app  # noqa: PLW0603
    autoregister()
    _click_app = get_command(app)


def main() -> None:
    """
    Main entry point for the CLI. Registers all the CLI commands and runs the app.
    """
    autoregister()
    app()
