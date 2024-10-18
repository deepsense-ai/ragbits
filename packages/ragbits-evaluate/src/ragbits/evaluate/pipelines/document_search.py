from dataclasses import dataclass
from functools import cached_property
from typing import Any, Optional

from datasets import load_dataset
from omegaconf import DictConfig
from tqdm.asyncio import tqdm

from ragbits.core.embeddings import LiteLLMEmbeddings
from ragbits.core.vector_store import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement

try:
    from ragbits.document_search import DocumentSearch
except ImportError:
    HAS_RAGBITS_DOCUMENT_SEARCH = False
else:
    HAS_RAGBITS_DOCUMENT_SEARCH = True

from .base import EvaluationPipeline, EvaluationResult


@dataclass
class DocumentSearchResult(EvaluationResult):
    """
    Represents the result of a single evaluation.
    """

    question: str
    reference_passages: list[str]
    predicted_passages: list[str]


class DocumentSearchPipeline(EvaluationPipeline):
    """
    Document search evaluation pipeline.
    """

    def __init__(self, config: Optional[DictConfig] = None) -> None:
        """
        Initializes the document search evaluation pipeline.

        Raises:
            ImportError: If the ragbits-document-search package is not installed.
        """
        super().__init__(config)
        if not HAS_RAGBITS_DOCUMENT_SEARCH:
            raise ImportError("You need to install the 'ragbits-document-search' package to use this pipeline.")

    @cached_property
    def documents(self) -> list[DocumentMeta]:
        """
        Returns the documents to be ingested.

        Returns:
            The documents to be ingested.
        """
        # TODO: Implement HF doc loader.
        docs = load_dataset(
            path=self.config.data.ingest.path,
            split=self.config.data.ingest.split,
        )
        return [DocumentMeta.create_text_document_from_literal(doc["content"]) for doc in docs]

    @cached_property
    def document_search(self) -> DocumentSearch:
        """
        Returns the document search instance.

        Returns:
            The document search instance.
        """
        return DocumentSearch(
            embedder=LiteLLMEmbeddings(),
            vector_store=InMemoryVectorStore(),
        )

    async def prepare(self) -> None:
        """
        Prepares the document search evaluation pipeline.
        """
        await tqdm.gather(
            *[self.document_search.ingest_document(document) for document in self.documents], desc="Ingestion"
        )

    async def __call__(self, data: dict[str, Any]) -> DocumentSearchResult:
        """
        Runs the document search evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
        elements = await self.document_search.search(data["question"])
        return DocumentSearchResult(
            question=data["question"],
            reference_passages=data["passages"],
            predicted_passages=[element.content for element in elements if isinstance(element, TextElement)],
        )
