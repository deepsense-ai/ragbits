from typing import Any

from distilabel.steps.tasks import TextGeneration

from ragbits.core.prompt.base import ChatFormat
from ragbits.evaluate.dataset_generator.utils import get_closest_substring, get_passages_list
from ragbits.evaluate.dataset_generator.prompt_passages_gen import PassagesGenInput, PassagesGenPrompt

class PassagesGenTask(TextGeneration):
    """
    A task for generating passages related to a specific question and answer from a text chunk.
    """

    get_matches: bool = False

    @property
    def inputs(self) -> list[str]:
        """Defines the input fields required for this task."""
        return ["chunk", "question", "basic_answer"]

    def format_input(self, input: dict[str, Any]) -> ChatFormat:
        """
        Formats the input data for generating passages based on the provided "chunk", "question", and
        "basic_answer" values.

        Args:
            input: A dictionary containing "chunk", "question", and "basic_answer".

        Returns:
            The formatted chat object containing the inputs for passage generation.
        """
        chat = PassagesGenPrompt(
            PassagesGenInput(
                question=input["question"],
                answer=input["basic_answer"],
                chunk=input["chunk"]
            )
        ).chat
        return chat

    @property
    def outputs(self) -> list[str]:
        """Defines the output fields generated by this task."""
        return ["question", "chunk", "passages"]

    def format_output(
        self, output: str, input: dict[str, Any] | None = None
    ) -> dict[str, list[str]]:
        """
        Formats the model's output into a structured dictionary with "question", "chunk", and "passages".
        If `get_matches` is `True`, attempts to find the closest matches for each passage within the
        provided chunk.

        Args:
            output: The raw output generated by the text generation model.
            input: Required if `get_matches` is `True`, containing "chunk"
                                           and "question".

        Returns:
            A dictionary with "chunk", "question", and a list of "passages".
        """
        passages = get_passages_list(output) or []

        if self.get_matches:
            matched_passages = []

            for passage in passages:
                if passage in input["chunk"]:
                    matched_passages.append(passage)
                else:
                    matched_passage = get_closest_substring(input["chunk"], passage)
                    matched_passages.append(matched_passage)

            return {"chunk": input["chunk"], "question": input["question"], "passages": matched_passages}

        return {"chunk": input["chunk"], "question": input["question"], "passages": passages}
