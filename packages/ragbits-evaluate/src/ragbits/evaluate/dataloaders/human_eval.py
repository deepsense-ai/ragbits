from collections.abc import Iterable

from ragbits.core.sources.base import Source
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.pipelines.human_eval import HumanEvalData


class HumanEvalDataLoader(DataLoader[HumanEvalData]):
    """
    HumanEval evaluation data loader.

    The source should point to a local/remote JSONL file in HumanEval format, where each line is a JSON object
    with at least the following keys: "
    - task_id" (str)
    - "prompt" (str)
    - "entry_point" (str)
    - "test" (str)
    """

    def __init__(
        self,
        source: Source,
        *,
        split: str = "data",
        task_id_key: str = "task_id",
        prompt_key: str = "prompt",
        entry_point_key: str = "entry_point",
        test_key: str = "test",
        canonical_solution_key: str | None = "canonical_solution",
    ) -> None:
        """
        Initialize the HumanEval data loader.

        Args:
            source: The source to load the data from.
            split: The split to load the data from.
            task_id_key: Dataset column with the HumanEval task identifier.
            prompt_key: Dataset column with the Python prompt (function signature and docstring).
            entry_point_key: Dataset column with the function name to evaluate.
            test_key: Dataset column with the Python test harness defining `check(candidate)`.
            canonical_solution_key: Optional dataset column with the reference solution (not used for scoring).
        """
        required = {task_id_key, prompt_key, entry_point_key, test_key}
        super().__init__(source=source, split=split, required_keys=required)
        self.task_id_key = task_id_key
        self.prompt_key = prompt_key
        self.entry_point_key = entry_point_key
        self.test_key = test_key
        self.canonical_solution_key = canonical_solution_key

    async def map(self, dataset: Iterable[dict]) -> Iterable[HumanEvalData]:
        """
        Map the dataset to the HumanEval evaluation data schema.

        Args:
            dataset: The dataset to map.

        Returns:
            The HumanEval evaluation data rows.
        """
        return [
            HumanEvalData(
                task_id=row.get(self.task_id_key, ""),
                prompt=row.get(self.prompt_key, ""),
                entry_point=row.get(self.entry_point_key, ""),
                test=row.get(self.test_key, ""),
                canonical_solution=(row.get(self.canonical_solution_key) if self.canonical_solution_key else None),
            )
            for row in dataset
        ]
