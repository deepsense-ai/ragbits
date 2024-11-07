from typing import Any
from distilabel.steps import StepInput

from .base import BaseFilter


DONT_KNOW_PHRASES: list[str] = [
    "I don't know",
    "I do not know",
    "don't know",
]


class DontKnowFilter(BaseFilter):
    def process(self, *inputs: StepInput) -> "StepOutput":
        result = [
            {input_type: inp[input_type] for input_type in inp} for inp in inputs[0] if not self._is_dont_know(inp)
        ]
        yield result

    @staticmethod
    def _is_dont_know(inp: dict[str, Any]) -> bool:
        return any(s.lower() in inp["basic_answer"].lower() for s in DONT_KNOW_PHRASES)
