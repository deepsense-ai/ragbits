from collections.abc import Iterable
from typing import Any

from ragbits.core.sources.base import Source
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.pipelines.hotpot_qa import HotpotQAData


class HotpotQADataLoader(DataLoader[HotpotQAData]):
    """
    HotpotQA evaluation data loader.

    The source should point to a local/remote JSON file exported from Hugging Face, where each example includes at
    least the following keys:
    - "id" (str)
    - "question" (str)
    - "answer" (str)
    - "type" ("bridge" | "comparison")
    - "level" ("easy" | "medium" | "hard")
    - "context" (object with keys: "title": list[str], "sentences": list[list[str]])
    """

    def __init__(
        self,
        source: Source,
        *,
        split: str = "data",
        id_key: str = "id",
        question_key: str = "question",
        answer_key: str = "answer",
        type_key: str = "type",
        level_key: str = "level",
        context_key: str = "context",
        # filter
        level_filter: str | None = None,  # one of: easy|medium|hard
    ) -> None:
        """
        Initialize the HotpotQA data loader.

        Args:
            source: The source to load the data from.
            split: The split to load the data from.
            id_key: Column with unique id.
            question_key: Column with question text.
            answer_key: Column with ground truth answer.
            type_key: Column with question type ("bridge" | "comparison").
            level_key: Column with difficulty ("easy" | "medium" | "hard").
            context_key: Column with context object containing titles and sentences.
            level_filter: If provided, return only examples with this level.
        """
        required = {id_key, question_key, answer_key, type_key, level_key, context_key}
        super().__init__(source=source, split=split, required_keys=required)
        self.id_key = id_key
        self.question_key = question_key
        self.answer_key = answer_key
        self.type_key = type_key
        self.level_key = level_key
        self.context_key = context_key
        self.level_filter = level_filter

    async def map(self, dataset: Iterable[dict]) -> Iterable[HotpotQAData]:
        """
        Map the dataset to the HotpotQA evaluation data schema.

        Args:
            dataset: The dataset to map.

        Returns:
            The HotpotQA evaluation data rows.
        """

        def to_context_rows(context: dict[str, Any]) -> list[str]:
            titles = context.get("title", []) or []
            sentences = context.get("sentences", []) or []
            rows: list[str] = []
            for title, sent_list in zip(titles, sentences, strict=False):
                doc_text = "\n".join(sent_list) if isinstance(sent_list, list) else str(sent_list)
                rows.append(f"{title}\n{doc_text}")
            if not rows and isinstance(sentences, list):
                flat = "\n".join([" ".join(s) if isinstance(s, list) else str(s) for s in sentences])
                rows = [flat]
            return rows

        return [
            HotpotQAData(
                id=row.get(self.id_key, ""),
                question=row.get(self.question_key, ""),
                reference_answer=str(row.get(self.answer_key, "")),
                qtype=str(row.get(self.type_key, "")),
                level=(row.get(self.level_key) or "").lower(),
                reference_context=to_context_rows(row.get(self.context_key, {}) or {}),
            )
            for row in dataset
            if not self.level_filter or (row.get(self.level_key, "").lower() == self.level_filter)
        ]
