# pylint: disable=import-outside-toplevel
import typer

prompts_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer, help_only: bool) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
        help_only: A boolean indicating whether it is a help-only run.
    """
    if not help_only:
        from .prompt.lab.app import lab_app
        from .prompt.promptfoo import generate_configs

        prompts_app.command(name="lab")(lab_app)
        prompts_app.command(name="generate-promptfoo-configs")(generate_configs)
    app.add_typer(prompts_app, name="prompts", help="Commands for managing prompts")
