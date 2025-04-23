from datasets import load_dataset

from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.pipelines.document_search import DocumentSearchData


class DocumentSearchDataLoader(DataLoader[DocumentSearchData]):
    """
    Document search evaluation data loader.

    The source used for this data loader should point to a file that can be loaded by [Hugging Face](https://huggingface.co/docs/datasets/loading#local-and-remote-files)
    and contain the following features: "question, "passages".
    """

    async def load(self) -> list[DocumentSearchData]:
        """
        Load the data from source and format them.

        Returns:
            The document search evaluation data.
        """
        data_path = await self.source.fetch()
        dataset = load_dataset(
            path=str(data_path.parent),
            split=data_path.stem,
        )
        return [
            DocumentSearchData(
                question=data["question"],
                reference_passages=data["chunks"],
            )
            for data in dataset
        ]
