import typer

from ragbits.chat.api import RagbitsAPI

ds_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(ds_app, name="api", help="Commands for running API service")


@ds_app.command()
def run(
    chat_interface: str = typer.Argument(..., help="Path to a module with chat function"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind the API server to"),
    port: int = typer.Option(8000, "--port", help="Port to bind the API server to"),
    cors_origins: list[str] = typer.Option(  # noqa: B008
        None,
        "--cors-origin",
        help="Allowed CORS origins. Can be specified multiple times.",
    ),
    ui_build_dir: str = typer.Option(
        None,
        "--ui-build-dir",
        help="Path to a custom UI build directory. If not specified, uses the default package UI.",
    ),
) -> None:
    """
    Run API service with UI demo
    """
    api = RagbitsAPI(
        chat_interface=chat_interface,
        cors_origins=cors_origins,
        ui_build_dir=ui_build_dir,
    )
    api.run(host=host, port=port)
