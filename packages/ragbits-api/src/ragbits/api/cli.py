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
def run():
    """
    Run API service with UI demo
    """
    api = RagbitsAPI()
    api.run()
    


    
    