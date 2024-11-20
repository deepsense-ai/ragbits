from typing import Any

from distilabel.steps import StepInput, StepOutput

from .base import BaseFilter

DONT_KNOW_PHRASES: list[str] = [
    "I don't know",
    "I do not know",
    "don't know",
]


class DontKnowFilter(BaseFilter):
    """A class for basic rule-based filtering of don't know anwers"""

    def process(self, *inputs: StepInput) -> "StepOutput":
        """
        Runs the basic rule-based filtering of the inputs
        Args:
            inputs - the outputs of some generation step
        Returns:
            outputs filtered to the ones that do not contain the pre-defined phrases
        """
        result = [
            {input_type: input_[input_type] for input_type in input_}
            for input_ in inputs[0]
            if not self._is_dont_know(input_)
        ]
        yield result

    @staticmethod
    def _is_dont_know(input_: dict[str, Any]) -> bool:
        return any(s.lower() in input_["basic_answer"].lower() for s in DONT_KNOW_PHRASES)
