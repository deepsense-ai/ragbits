import json
import os
from typing import Annotated

import typer
from fastapi.openapi.utils import get_openapi
from rich import print as rprint
from rich.console import Console
from rich.syntax import Syntax

from ragbits.core.utils.config_handling import import_by_path
from ragbits.integration_servers import IntegrationServerBuilder


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    integrations = typer.Typer()
    app.add_typer(integrations, name="integrations")

    @integrations.command()
    def expose_tool(
        factory_path: Annotated[
            str,
            typer.Argument(
                help="Python path to a function that creates a vector store, ina format 'module.submodule:function'"
            ),
        ],
        tool_name: str | None = None,
        tool_description: str | None = None,
        tunnel: bool = False,
        hostname: str | None = None,

    ) -> None:
        """
        Search for documents.
        """
        tool = import_by_path(factory_path, default_module=None)()

        server = IntegrationServerBuilder().add_tool(tool, name=tool_name, description=tool_description).build()

        openapi_schema = get_openapi(title="FastAPI", version="2.5.0", routes=server.routes)

        if tunnel:
            try:
                import ngrok
            except ImportError:
                raise ImportError("To use the --tunnel option, you need to install the ngrok package.")

            if os.environ.get("NGROK_AUTHTOKEN") is None:
                raise ValueError(
                    "To use the --tunnel option, you need to set the NGROK_AUTHTOKEN environment variable."
                )

            listener = ngrok.forward(9999, authtoken_from_env=True)
            openapi_schema["servers"] = [{"url": listener.url()}]
            rprint(f"\n[cyan]Started ngrok tunnel on port 9999. External address: [b]{listener.url()}[/b]\n")
        elif hostname:
            openapi_schema["servers"] = [{"url": hostname}]

        rprint("\n[cyan bold]OpenAPI schema for the tool:\n")
        Console().print(Syntax(json.dumps(openapi_schema), "json", theme="monokai", line_numbers=True, word_wrap=True))

        import uvicorn
        uvicorn.run(server, host="0.0.0.0", port=9999)
