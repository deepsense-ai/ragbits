import asyncio

from datasets import load_dataset

from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.evaluate.metrics import MetricSet

DS_PRECISION_RECALL_F1 = {
    "precision_recall_f1": ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
            "config": {
                "matching_strategy": {
                    "type": "RougeChunkMatch",
                    "config": {
                        "threshold": 0.5,
                    },
                },
            },
        }
    ),
}


def precision_recall_f1() -> MetricSet:
    """A factory of precision recall f1 metric set for retrival evaluation"""
    return MetricSet.from_config(config=DS_PRECISION_RECALL_F1)


async def _add_example_documents(document_search: DocumentSearch) -> None:
    dataset = load_dataset(path="deepsense-ai/synthetic-rag-dataset_v1.0", split="train")
    documents = [DocumentMeta.create_text_document_from_literal(doc) for chunks in dataset["chunks"] for doc in chunks]
    await document_search.ingest(documents)


def basic_document_search_factory() -> DocumentSearch:
    """A factory for basic example document search instance"""
    document_search = DocumentSearch(vector_store=InMemoryVectorStore(embedder=LiteLLMEmbedder()))
    asyncio.run(_add_example_documents(document_search))
    return document_search
