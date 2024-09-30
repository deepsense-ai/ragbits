import typer

from .prompt_lab.app import lab_app

prompts_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    prompts_app.command(name="lab")(lab_app)
    app.add_typer(prompts_app, name="prompts", help="Commands for managing prompts")
