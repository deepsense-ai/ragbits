import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
from pydantic import BaseModel

from ragbits.cli import cli_state, print_output
from ragbits.cli._utils import get_instance_or_exit
from ragbits.cli.state import OutputType
from ragbits.core.vector_stores.base import VectorStore, VectorStoreOptions

vector_stores_app = typer.Typer(no_args_is_help=True)


@dataclass
class CLIState:
    vector_store: VectorStore | None = None


state: CLIState = CLIState()

# Default columns for commands that list entries
_default_entry_columns = "id,text,metadata"

# Default columns for commands that lists results
_default_result_columns = "score,entry.id,entry.text,entry.metadata"


@vector_stores_app.callback()
def common_args(
    factory_path: Annotated[
        str | None,
        typer.Option(
            help="Python path to a function that creates a vector store, in a 'module.submodule:function' format"
        ),
    ] = None,
    yaml_path: Annotated[
        Path | None,
        typer.Option(help="Path to a YAML configuration file for the vector store", exists=True, resolve_path=True),
    ] = None,
) -> None:
    state.vector_store = get_instance_or_exit(
        VectorStore,
        factory_path=factory_path,
        yaml_path=yaml_path,
    )


@vector_stores_app.command(name="list")
def list_entries(
    limit: Annotated[int, typer.Option(help="Maximum number of entries to list")] = 10,
    offset: Annotated[int, typer.Option(help="How many entries to skip")] = 0,
    columns: Annotated[
        str,
        typer.Option(help="Comma-separated list of columns to display, aviailable: id, text, image_bytes, metadata"),
    ] = _default_entry_columns,
) -> None:
    """
    List all objects in the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")

        entries = await state.vector_store.list(limit=limit, offset=offset)
        print_output(entries, columns=columns)

    asyncio.run(run())


class RemovedItem(BaseModel):
    id: UUID


@vector_stores_app.command()
def remove(
    ids: Annotated[list[UUID], typer.Argument(help="IDs of the entries to remove from the vector store")],
) -> None:
    """
    Remove objects from the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")

        await state.vector_store.remove(ids)
        if cli_state.output_type == OutputType.text:
            typer.echo(f"Removed entries with IDs: {', '.join(str(id) for id in ids)}")
        else:
            print_output([RemovedItem(id=id) for id in ids])

    asyncio.run(run())


@vector_stores_app.command()
def query(
    text: Annotated[str, typer.Argument(help="Text to query the vector store with")],
    k: Annotated[int, typer.Option(help="Number of entries to retrieve")] = 5,
    score_threshold: Annotated[float | None, typer.Option(help="Minimum score for result to be returned")] = None,
    columns: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of columns to display, "
            "aviailable: score, entry.id, entry.text, entry.image_bytes, entry.metadata"
        ),
    ] = _default_result_columns,
) -> None:
    """
    Query the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")
        options = VectorStoreOptions(k=k, score_threshold=score_threshold)

        entries = await state.vector_store.retrieve(
            text=text,
            options=options,
        )
        print_output(entries, columns=columns)

    asyncio.run(run())
