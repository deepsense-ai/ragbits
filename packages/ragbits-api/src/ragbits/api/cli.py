import os
import typer

from ragbits.api._main import RagbitsAPI
 
ds_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(ds_app, name="api", help="Commands for running API service")


@ds_app.command()
def run(chat_path: str = typer.Option(..., "--chat-path", help="Path to a module with chat function")):
    """
    Run API service with UI demo
    """

    api = RagbitsAPI()
    api.initialize_chat_module(chat_path=chat_path)
    api.run()
    


    
    