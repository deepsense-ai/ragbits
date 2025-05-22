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

    def __init__(self, source: Source, question_key: str = "question", passages_key: str = "passages") -> None:
        """
        Initialize the document search data loader.

        Args:
            source: The source to load the data from.
            question_key: The dataset column name that contains the question.
            passages_key: The dataset column name that contains the passages. Passages are optional.
        """
        super().__init__(source)
        self.question_key = question_key
        self.passages_key = passages_key

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
                reference_passages=data.get(self.passages_key),
            )
            for data in dataset
        ]
