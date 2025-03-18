import asyncio

import pytest
from typer.testing import CliRunner

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.evaluate.cli import eval_app

factory_path = f"{__name__}:create_document_search_instance_with_documents"
target_cls = "ragbits.document_search:DocumentSearch"


@pytest.fixture
def dataloader_args() -> str:
    """Arguments for dataloader"""
    return "deepsense-ai/synthetic-rag-dataset_v1.0,train"


async def _add_example_documents(document_search: DocumentSearch) -> None:
    documents = [
        DocumentMeta.create_text_document_from_literal("Foo document"),
        DocumentMeta.create_text_document_from_literal("Bar document"),
        DocumentMeta.create_text_document_from_literal("Baz document"),
    ]
    await document_search.ingest(documents)


def create_document_search_instance_with_documents() -> DocumentSearch:
    document_search = DocumentSearch(vector_store=InMemoryVectorStore(embedder=NoopEmbedder()))
    asyncio.run(_add_example_documents(document_search))
    return document_search


def test_run_evaluation(dataloader_args: str) -> None:
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        eval_app,
        [
            "--target-factory-path",
            factory_path,
            "--target-cls",
            target_cls,
            "--dataloader-args",
            dataloader_args,
            "run-evaluation",
        ],
    )
    assert result.exit_code == 0
