from collections.abc import Iterable

from datasets import load_dataset

from ragbits.core.sources.base import Source
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.dataloaders.exceptions import DataLoaderIncorrectFormatDataError
from ragbits.evaluate.pipelines.document_search import DocumentSearchData


class DocumentSearchDataLoader(DataLoader[DocumentSearchData]):
    """
    Document search evaluation data loader.

    The source used for this data loader should point to a file that can be loaded by [Hugging Face](https://huggingface.co/docs/datasets/loading#local-and-remote-files)
    and contain the following features: "question, "passages".
    """

    def __init__(
        self,
        source: Source,
        question_key: str = "question",
        document_ids_key: str = "document_ids",
        passages_key: str = "passages",
        page_numbers_key: str = "page_numbers",
    ) -> None:
        """
        Initialize the document search data loader.

        Args:
            source: The source to load the data from.
            question_key: The dataset column name that contains the question.
            document_ids_key: The dataset column name that contains the document ids. Document ids are optional.
            passages_key: The dataset column name that contains the passages. Passages are optional.
            page_numbers_key: The dataset column name that contains the page numbers. Page numbers are optional.
        """
        super().__init__(source)
        self.question_key = question_key
        self.document_ids_key = document_ids_key
        self.passages_key = passages_key
        self.page_numbers_key = page_numbers_key

    async def load(self) -> Iterable[DocumentSearchData]:
        """
        Load the data from source and format them.

        Returns:
            The document search evaluation data.

        Raises:
            DataLoaderIncorrectFormatDataError: If evaluation dataset is incorrectly formatted.
        """
        data_path = await self.source.fetch()
        dataset = load_dataset(
            path=str(data_path.parent),
            split="train",
            data_files={"train": str(data_path.name)},
        )
        if self.question_key not in dataset.features:
            raise DataLoaderIncorrectFormatDataError(
                required_features=[self.question_key],
                data_path=data_path,
            )

        return [
            DocumentSearchData(
                question=data.get(self.question_key),
                reference_document_ids=data.get(self.document_ids_key),
                reference_passages=data.get(self.passages_key),
                reference_page_numbers=data.get(self.page_numbers_key),
            )
            for data in dataset
        ]
