import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from ragbits.cli import cli_state, print_output
from ragbits.cli._utils import get_instance_or_exit
from ragbits.cli.state import OutputType
from ragbits.core.embeddings.base import Embeddings
from ragbits.core.vector_stores.base import VectorStore, VectorStoreOptions

vector_stores_app = typer.Typer(no_args_is_help=True)


@dataclass
class CLIState:
    vector_store: VectorStore | None = None


state: CLIState = CLIState()

# Default columns for commands that list entries
_default_columns = "id,key,metadata"


@vector_stores_app.callback()
def common_args(
    factory_path: Annotated[
        str | None,
        typer.Option(
            help="Python path to a function that creates a vector store, ina format 'module.submodule:function'"
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
        str, typer.Option(help="Comma-separated list of columns to display, aviailable: id, key, vector, metadata")
    ] = _default_columns,
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
    id: str


@vector_stores_app.command()
def remove(
    ids: Annotated[list[str], typer.Argument(help="IDs of the entries to remove from the vector store")],
) -> None:
    """
    Remove objects from the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")

        await state.vector_store.remove(ids)
        if cli_state.output_type == OutputType.text:
            typer.echo(f"Removed entries with IDs: {', '.join(ids)}")
        else:
            print_output([RemovedItem(id=id) for id in ids])

    asyncio.run(run())


@vector_stores_app.command()
def query(
    text: Annotated[str, typer.Argument(help="Text to query the vector store with")],
    k: Annotated[int, typer.Option(help="Number of entries to retrieve")] = 5,
    max_distance: Annotated[float | None, typer.Option(help="Maximum distance to the query vector")] = None,
    embedder_factory_path: Annotated[
        str | None,
        typer.Option(
            help="Python path to a function that creates an embedder, in a format 'module.submodule:function'"
        ),
    ] = None,
    embedder_yaml_path: Annotated[
        Path | None,
        typer.Option(help="Path to a YAML configuration file for the embedder", exists=True, resolve_path=True),
    ] = None,
    columns: Annotated[
        str, typer.Option(help="Comma-separated list of columns to display, aviailable: id, key, vector, metadata")
    ] = _default_columns,
) -> None:
    """
    Query the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")

        embedder = get_instance_or_exit(
            Embeddings,
            factory_path=embedder_factory_path,
            yaml_path=embedder_yaml_path,
            factory_path_argument_name="--embedder_factory_path",
            yaml_path_argument_name="--embedder_yaml_path",
            type_name="embedder",
        )
        search_vector = await embedder.embed_text([text])

        options = VectorStoreOptions(k=k, max_distance=max_distance)
        entries = await state.vector_store.retrieve(
            vector=search_vector[0],
            options=options,
        )
        print_output(entries, columns=columns)

    asyncio.run(run())
