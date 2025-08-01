from openai import AsyncOpenAI

from ragbits.core.prompt import Prompt
from ragbits.guardrails.base import Guardrail, GuardrailVerificationResult


class OpenAIModerationGuardrail(Guardrail):
    """
    Guardrail based on OpenAI moderation
    """

    def __init__(self, moderation_model: str = "omni-moderation-latest"):
        self._openai_client = AsyncOpenAI()
        self._moderation_model = moderation_model

    async def verify(self, input_to_verify: Prompt | str) -> GuardrailVerificationResult:
        """
        Verifies whether provided input meets certain criteria

        Args:
            input_to_verify: prompt or output of the model to check

        Returns:
            verification result
        """
        if isinstance(input_to_verify, Prompt):
            inputs = [{"type": "text", "text": input_to_verify.rendered_user_prompt}]

            if input_to_verify.rendered_system_prompt is not None:
                inputs.append({"type": "text", "text": input_to_verify.rendered_system_prompt})

            if attachments := input_to_verify.attachments:
                messages = [input_to_verify.create_message_with_attachment(attachment) for attachment in attachments]
                inputs.extend(messages)
        else:
            inputs = [{"type": "text", "text": input_to_verify}]
        response = await self._openai_client.moderations.create(model=self._moderation_model, input=inputs)  # type: ignore

        fail_reasons = [result for result in response.results if result.flagged]
        return GuardrailVerificationResult(
            guardrail_name=self.__class__.__name__,
            succeeded=len(fail_reasons) == 0,
            fail_reason=None if len(fail_reasons) == 0 else str(fail_reasons),
        )
