import sys
from abc import ABC, abstractmethod
from typing import Any

from distilabel.models import LLM
from distilabel.steps.tasks import TextGeneration

from ragbits.core.prompt import ChatFormat, Prompt
from ragbits.core.utils.config_handling import import_by_path

module = sys.modules[__name__]


class BaseDistilabelTask(TextGeneration, ABC):
    """Base class for distilabel TextGeneration tasks"""

    def __init__(self, llm: LLM, inputs: list[str], outputs: list[str], prompt_class: str | type[Prompt]):
        super().__init__(llm=llm)
        self._inputs = inputs
        self._outputs = outputs
        self._prompt_class = import_by_path(prompt_class, module) if isinstance(prompt_class, str) else prompt_class

    @property
    def inputs(self) -> list[str]:
        """
        Property describing input fields for a task
        Returns:
            list of input fields for a task
        """
        return self._inputs

    @property
    def outputs(self) -> list[str]:
        """
        Property describing output fields of the task
        Returns:
            list of outputs for a task
        """
        return self._outputs

    def format_input(self, input: dict[str, Any]) -> ChatFormat:
        """
        Formats the input data for generating a question based on the provided "chunk".

        Args:
            input: A dictionary containing a single "chunk" key with the text input.

        Returns:
            The formatted chat object containing the input for query generation.
        """
        chat = self._prompt_class(self._prompt_class.input_type(**input)).chat  # type: ignore
        return chat

    @abstractmethod
    def format_output(self, output: str, input: dict[str, Any] | None = None) -> dict[str, str | list[str]]:
        """
        Formats the generated question into a structured dictionary with the original "chunk" input.

        Args:
            output: The generated question.
            input: Optional; contains "chunk" key with the original input chunk.

        Returns:
            A dictionary containing "chunk" and "question".
        """
        pass
