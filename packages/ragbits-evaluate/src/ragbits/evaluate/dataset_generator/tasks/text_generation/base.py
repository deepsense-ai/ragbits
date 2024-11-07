from abc import ABC, abstractmethod
from typing import Any
from distilabel.steps.tasks import TextGeneration
from distilabel.llms.base import LLM
from ragbits.core.prompt import Prompt, ChatFormat


class BaseDistilabelTask(TextGeneration, ABC):
    def __init__(self, llm: LLM, inputs: list[str], outputs: list[str], prompt_class: type[Prompt], **kwargs):
        super().__init__(llm=llm)
        self._inputs = inputs
        self._outputs = outputs
        self._prompt_class = prompt_class

    @property
    def inputs(self):
        return self._inputs

    @property
    def outputs(self) -> list[str]:
        return self._outputs

    def format_input(self, input: dict[str, Any]) -> ChatFormat:
        """
        Formats the input data for generating a question based on the provided "chunk".

        Args:
            input: A dictionary containing a single "chunk" key with the text input.

        Returns:
            The formatted chat object containing the input for query generation.
        """
        chat = self._prompt_class(self._prompt_class.input_type(**input)).chat
        return chat

    @abstractmethod
    def format_output(self, output: str, input: dict[str, Any] | None = None) -> dict[str, str]:
        """
        Formats the generated question into a structured dictionary with the original "chunk" input.

        Args:
            output: The generated question.
            input: Optional; contains "chunk" key with the original input chunk.

        Returns:
            A dictionary containing "chunk" and "question".
        """
        pass
