import asyncio
from dataclasses import dataclass
from pathlib import Path

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


@vector_stores_app.callback()
def common_args(
    factory_path: str | None = None,
    yaml_path: Path | None = None,
) -> None:
    state.vector_store = get_instance_or_exit(
        VectorStore,
        factory_path=factory_path,
        yaml_path=yaml_path,
    )


@vector_stores_app.command(name="list")
def list_entries(limit: int = 10, offset: int = 0) -> None:
    """
    List all objects in the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")

        entries = await state.vector_store.list(limit=limit, offset=offset)
        print_output(entries)

    asyncio.run(run())


class RemovedItem(BaseModel):
    id: str


@vector_stores_app.command()
def remove(ids: list[str]) -> None:
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
    text: str,
    k: int = 5,
    max_distance: float | None = None,
    embedder_factory_path: str | None = None,
    embedder_yaml_path: Path | None = None,
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
        print_output(entries)

    asyncio.run(run())
