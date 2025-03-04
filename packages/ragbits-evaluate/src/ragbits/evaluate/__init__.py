from abc import ABC
from dataclasses import dataclass


@dataclass
class EvaluationResult(ABC):
    """
    Represents the result of a single evaluation.
    """