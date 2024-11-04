from abc import ABC, abstractmethod

from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class GuardrailVerificationResult(BaseModel):
    """
    Class representing result of guardrail verification
    """

    guardrail_name: str
    succeeded: bool
    fail_reason: str | None


class Guardrail(ABC):
    """
    Abstract class representing guardrail
    """

    @abstractmethod
    async def verify(self, input_to_verify: Prompt | str) -> GuardrailVerificationResult:
        """
        Verifies whether provided input meets certain criteria

        Args:
            input_to_verify: prompt or output of the model to check

        Returns:
            verification result
        """


class GuardrailManager:
    """
    Class responsible for running guardrails
    """

    def __init__(self, guardrails: list[Guardrail]):
        self._guardrails = guardrails

    async def verify(self, input_to_verify: Prompt | str) -> list[GuardrailVerificationResult]:
        """
        Verifies whether provided input meets certain criteria

        Args:
            input_to_verify: prompt or output of the model to check

        Returns:
            list of verification result
        """
        return [await guardrail.verify(input_to_verify) for guardrail in self._guardrails]
