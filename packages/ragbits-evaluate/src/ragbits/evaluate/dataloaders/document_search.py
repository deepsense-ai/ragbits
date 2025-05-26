from collections.abc import Iterable

from ragbits.core.sources.base import Source
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.pipelines.document_search import DocumentSearchData


class DocumentSearchDataLoader(DataLoader[DocumentSearchData]):
    """
    Document search evaluation data loader.

    The source used for this data loader should point to a file that can be loaded by [Hugging Face](https://huggingface.co/docs/datasets/loading#local-and-remote-files).
    """

    def __init__(
        self,
        source: Source,
        *,
        split: str = "data",
        question_key: str = "question",
        document_ids_key: str = "document_ids",
        passages_key: str = "passages",
        page_numbers_key: str = "page_numbers",
    ) -> None:
        """
        Initialize the document search data loader.

        Args:
            source: The source to load the data from.
            split: The split to load the data from. Split is fixed for data loaders to "data",
                but you can slice it using the [Hugging Face API](https://huggingface.co/docs/datasets/v1.11.0/splits.html#slicing-api).
            question_key: The dataset column name that contains the question.
            document_ids_key: The dataset column name that contains the document ids. Document ids are optional.
            passages_key: The dataset column name that contains the passages. Passages are optional.
            page_numbers_key: The dataset column name that contains the page numbers. Page numbers are optional.
        """
        super().__init__(source=source, split=split, required_keys={question_key})
        self.question_key = question_key
        self.document_ids_key = document_ids_key
        self.passages_key = passages_key
        self.page_numbers_key = page_numbers_key

    async def map(self, dataset: Iterable[dict]) -> Iterable[DocumentSearchData]:
        """
        Map the dataset to the document search data schema.

        Args:
            dataset: The dataset to map.

        Returns:
            The document search data.
        """
        return [
            DocumentSearchData(
                question=data.get(self.question_key, ""),
                reference_document_ids=data.get(self.document_ids_key),
                reference_passages=data.get(self.passages_key),
                reference_page_numbers=data.get(self.page_numbers_key),
            )
            for data in dataset
        ]
