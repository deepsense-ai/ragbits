from typer import Typer

prompts_app = Typer()


@prompts_app.command()
def placeholder() -> None:
    """Placeholder command"""
    print("foo")


def register(app: Typer) -> None:
    """
    Register the CLI commands for the ragbits-core package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(prompts_app, name="prompts")
