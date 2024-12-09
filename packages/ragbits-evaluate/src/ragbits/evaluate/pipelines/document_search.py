import asyncio
import uuid
from dataclasses import dataclass
from functools import cached_property

from omegaconf import DictConfig
from tqdm.asyncio import tqdm

from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.sources import HuggingFaceSource
from ragbits.evaluate.pipelines.base import EvaluationPipeline, EvaluationResult


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

    @cached_property
    def document_search(self) -> "DocumentSearch":
        """
        Returns the document search instance.

        Returns:
            The document search instance.
        """
        return DocumentSearch.from_config(self.config)  # type: ignore

    async def __call__(self, data: dict) -> DocumentSearchResult:
        """
        Runs the document search evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
        elements = await self.document_search.search(data["question"])
        predicted_passages = [element.text_representation or "" for element in elements]
        return DocumentSearchResult(
            question=data["question"],
            reference_passages=data["passages"],
            predicted_passages=predicted_passages,
        )


class DocumentSearchWithIngestionPipeline(DocumentSearchPipeline):
    """
    A class for joint doument ingestion and search
    """

    def __init__(self, config: DictConfig | None = None) -> None:
        super().__init__(config)
        self.config.vector_store.config.index_name = str(uuid.uuid4())
        self._ingested = False
        self._lock = asyncio.Lock()

    async def __call__(self, data: dict) -> DocumentSearchResult:
        """
        Queries a vector store with given data
        Ingests the corpus to the store if has not been done
        Args:
            data: dict - query
        Returns:
            DocumentSearchResult - query result
        """
        async with self._lock:
            if not self._ingested:
                await self._ingest_documents()
                self._ingested = True
        return await super().__call__(data)

    async def _ingest_documents(self) -> None:
        documents = await tqdm.gather(
            *[
                DocumentMeta.from_source(
                    HuggingFaceSource(
                        path=self.config.answer_data_source.path,
                        split=self.config.answer_data_source.split,
                        row=i,
                    )
                )
                for i in range(self.config.answer_data_source.num_docs)
            ],
            desc="Download",
        )
        await self.document_search.ingest(documents)
