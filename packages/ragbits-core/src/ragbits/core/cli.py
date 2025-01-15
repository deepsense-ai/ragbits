import typer

from ragbits.core.prompt._cli import prompts_app
from ragbits.core.vector_stores._cli import vector_stores_app


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(prompts_app, name="prompts", help="Commands for managing prompts")
    app.add_typer(vector_stores_app, name="vector-store", help="Commands for managing vector stores")
