from abc import ABC, abstractmethod
from distilabel.steps import Step, StepInput, StepOutput
from ..text_generation.base import BaseDistilabelTask


class BaseFilter(Step, ABC):
    def __init__(self, task: BaseDistilabelTask, **kwargs):
        super().__init__(**kwargs)
        self._task = task

    @property
    def inputs(self) -> "StepColumns":
        return self._task.outputs

    @property
    def outputs(self) -> "StepColumns":
        return self._task.outputs

    @abstractmethod
    def process(self, *inputs: StepInput) -> "StepOutput":
        pass