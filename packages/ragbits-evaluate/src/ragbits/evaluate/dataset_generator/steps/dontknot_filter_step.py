from typing import Any, Dict, List

from pydantic import Field

from distilabel.steps.base import GeneratorStep


def dontknow_filter_rule_based(row: dict[str, Any], dont_know_phrases: list[str]) -> bool:
    return not any(phrase in s for phrase in dont_know_phrases for s in row["basic_answer"])


class DontKnowFilter(GeneratorStep):
    data: list[dict[str, Any]] = Field(default_factory=list, exclude=True)
    dont_know_phrases: list[str] = [
        "I don't know",
        "I do not know",
        "don't know",
    ]

    @staticmethod
    def _transform_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # TODO
        pass

    @property
    def outputs(self) -> List[str]:
        # TODO
        pass
