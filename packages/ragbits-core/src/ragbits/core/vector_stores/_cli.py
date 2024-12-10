import asyncio
from dataclasses import dataclass
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console

from ragbits.cli import cli_state, print_output
from ragbits.cli.state import OutputType
from ragbits.core.config import core_config
from ragbits.core.embeddings.base import Embeddings
from ragbits.core.utils.config_handling import InvalidConfigError
from ragbits.core.vector_stores.base import VectorStore, VectorStoreOptions

vector_stores_app = typer.Typer(no_args_is_help=True)


@dataclass
class CLIState:
    vector_store: VectorStore | None = None


state: CLIState = CLIState()


@vector_stores_app.callback()
def common_args(
    factory_path: str | None = None,
    yaml_path: str | None = None,
) -> None:
    try:
        state.vector_store = VectorStore.subclass_from_defaults(
            core_config,
            factory_path_override=factory_path,
            yaml_path_override=Path.cwd() / yaml_path if yaml_path else None,
        )
    except InvalidConfigError as e:
        Console(stderr=True).print(e)
        raise typer.Exit(1) from e


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
    embedder_yaml_path: str | None = None,
) -> None:
    """
    Query the chosen vector store.
    """

    async def run() -> None:
        if state.vector_store is None:
            raise ValueError("Vector store not initialized")

        try:
            embedder = Embeddings.subclass_from_defaults(
                core_config,
                factory_path_override=embedder_factory_path,
                yaml_path_override=Path.cwd() / embedder_yaml_path if embedder_yaml_path else None,
            )
        except InvalidConfigError as e:
            Console(stderr=True).print(e)
            raise typer.Exit(1) from e

        search_vector = await embedder.embed_text([text])

        options = VectorStoreOptions(k=k, max_distance=max_distance)
        entries = await state.vector_store.retrieve(
            vector=search_vector[0],
            options=options,
        )
        print_output(entries)

    asyncio.run(run())
