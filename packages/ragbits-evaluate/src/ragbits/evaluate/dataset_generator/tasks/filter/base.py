from abc import ABC, abstractmethod

from distilabel.steps import Step, StepInput, StepOutput

from ..corpus_generation import CorpusGenerationStep
from ..text_generation.base import BaseDistilabelTask


class BaseFilter(Step, ABC):
    """Base class for filtering the outputs of pipeline steps"""

    def __init__(self, task: BaseDistilabelTask | CorpusGenerationStep):
        super().__init__()
        self._task = task

    @property
    def inputs(self) -> list[str]:
        """
        Property describing input fields for a filter
        Returns:
            list of input fields for a filter
        """
        return self._task.outputs

    @property
    def outputs(self) -> list[str]:
        """
        Property describing output fields for a filter
        Returns:
            list of output fields for a filter
        """
        return self._task.outputs

    @abstractmethod
    def process(self, *inputs: StepInput) -> "StepOutput":
        """
        Abstract method for filter step processing
        Args:
            inputs - inputs to a filter
        Returns:
            filtered outputs
        """
        pass
