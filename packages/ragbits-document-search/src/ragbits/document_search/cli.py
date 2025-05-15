import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from ragbits.cli._utils import get_instance_or_exit
from ragbits.cli.state import print_output
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.document_search._main import DocumentSearch, DocumentSearchOptions

ds_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(ds_app, name="document-search", help="Commands for interacting with the document search")


@dataclass
class _CLIState:
    document_search: DocumentSearch | None = None


state: _CLIState = _CLIState()

# Default columns for commands that list entries
_default_columns = "element_type,key"


class IngestedItem(BaseModel):
    """Model describing ingested source"""

    source: str


@ds_app.callback()
def common_args(
    factory_path: Annotated[
        str | None,
        typer.Option(
            help="Python path to a function that creates a document search object, "
            "in a 'module.submodule:function' format"
        ),
    ] = None,
    yaml_path: Annotated[
        Path | None,
        typer.Option(help="Path to a YAML configuration file for the document search", exists=True, resolve_path=True),
    ] = None,
) -> None:
    """
    Common arguments for the document search commands.
    """
    state.document_search = get_instance_or_exit(
        DocumentSearch,
        factory_path=factory_path,
        yaml_path=yaml_path,
    )


@ds_app.command()
def search(
    query: Annotated[str, typer.Argument(help="Text to query with")],
    k: Annotated[int, typer.Option(help="Number of entries to retrieve")] = 5,
    columns: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of columns to display, "
            "available: id, element_type, key, location, text_representation, document_meta"
        ),
    ] = _default_columns,
) -> None:
    """
    Query the chosen vector store.
    """

    async def run() -> None:
        if state.document_search is None:
            raise ValueError("Document search not initialized")

        options: DocumentSearchOptions = DocumentSearchOptions(vector_store_options=VectorStoreOptions(k=k))
        entries = await state.document_search.search(query, options)
        print_output(entries, columns=columns)

    asyncio.run(run())


@ds_app.command()
def ingest(
    source: Annotated[str, typer.Argument(help="Source pattern")],
) -> None:
    """
    Ingest the elements from a given source to vector store.
    """

    async def run() -> None:
        if state.document_search is None:
            raise ValueError("Document search not initialized")
        await state.document_search.ingest(source)
        print_output(IngestedItem(source=source))

    asyncio.run(run())
