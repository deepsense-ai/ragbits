from collections.abc import Iterable

from ragbits.core.sources.base import Source
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.pipelines.question_answer import QuestionAnswerData


class QuestionAnswerDataLoader(DataLoader[QuestionAnswerData]):
    """
    Question answer evaluation data loader.

    The source used for this data loader should point to a file that can be loaded by [Hugging Face](https://huggingface.co/docs/datasets/loading#local-and-remote-files).
    """

    def __init__(
        self,
        source: Source,
        *,
        split: str = "data",
        question_key: str = "question",
        answer_key: str = "answer",
        context_key: str = "context",
    ) -> None:
        """
        Initialize the question answer data loader.

        Args:
            source: The source to load the data from.
            split: The split to load the data from.
            question_key: The dataset column name that contains the question.
            answer_key: The dataset column name that contains the answer.
            context_key: The dataset column name that contains the context. Context is optional.
        """
        super().__init__(source=source, split=split, required_keys={question_key, answer_key})
        self.question_key = question_key
        self.answer_key = answer_key
        self.context_key = context_key

    async def map(self, dataset: Iterable[dict]) -> Iterable[QuestionAnswerData]:
        """
        Map the dataset to the question answer data schema.

        Args:
            dataset: The dataset to map.

        Returns:
            The question answer data.
        """
        return [
            QuestionAnswerData(
                question=data.get(self.question_key, ""),
                reference_answer=data.get(self.answer_key, ""),
                reference_context=data.get(self.context_key),
            )
            for data in dataset
        ]
