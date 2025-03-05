import asyncio

from typer.testing import CliRunner

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.evaluate.cli import eval_app


factory_path = f"{__name__}:create_document_search_instance_with_documents"
target_cls = "ragbits.document_search:DocumentSearch"


async def _add_example_documents(document_search: DocumentSearch) -> None:
    documents = [
        DocumentMeta.create_text_document_from_literal("Foo document"),
        DocumentMeta.create_text_document_from_literal("Bar document"),
        DocumentMeta.create_text_document_from_literal("Baz document"),
    ]
    await document_search.ingest(documents)


def create_document_search_instance_with_documents():
    document_search = DocumentSearch(embedder=NoopEmbedder(), vector_store=InMemoryVectorStore())
    asyncio.run(_add_example_documents(document_search))
    return document_search


def test_run_evaluation() -> None:
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        eval_app,
        [
            "--target-factory-path",
            factory_path,
            "--target-cls",
            target_cls,
            "--dataloader-args",
            "deepsense-ai/synthetic-rag-dataset_v1.0,train",
            "run-evaluation",
        ],
    )
    assert result.exit_code == 0
