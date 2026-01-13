import asyncio

from ragbits.agents import Agent, AgentResult, PostProcessor
from ragbits.agents._main import AgentOptions, AgentRunContext
from ragbits.core.llms.litellm import LiteLLM
from ragbits.guardrails.base import Guardrail, GuardrailManager, GuardrailVerificationResult
from ragbits.guardrails.openai_moderation import OpenAIModerationGuardrail


class GuardrailPostProcessor(PostProcessor):
    """
    Post-processor that uses Ragbits GuardrailManager to enforce guardrails.

    This demonstrates using the built-in guardrails system to validate agent output.
    Use case: Enforcing guardrails (moderation, content policy) using Ragbits guardrails.
    """

    def __init__(self, guardrails: list[Guardrail], fail_on_violation: bool = False) -> None:
        """
        Initialize with guardrails.

        Args:
            guardrails: List of Guardrail instances to apply
            fail_on_violation: Whether to raise an exception on guardrail violation
        """
        self.manager = GuardrailManager(guardrails)
        self.fail_on_violation = fail_on_violation

    async def process(
        self,
        result: AgentResult,
        agent: Agent,
        options: AgentOptions | None = None,
        context: AgentRunContext | None = None,
    ) -> AgentResult:
        """
        Apply guardrails to agent output.

        Args:
            result: The agent result to process
            agent: The agent instance
            options: Optional agent options
            context: Optional agent run context

        Returns:
            Modified agent result with guardrail verification metadata

        Raises:
            ValueError: If fail_on_violation=True and any guardrail fails
        """
        content = result.content

        # Verify content against all guardrails
        verification_results = await self.manager.verify(content)

        # Check if any guardrail failed
        failed_guardrails = [v for v in verification_results if not v.succeeded]
        all_passed = len(failed_guardrails) == 0

        # Modify content if guardrails failed
        modified_content = content
        if not all_passed:
            if self.fail_on_violation:
                raise ValueError(f"Guardrail violation detected: {[g.fail_reason for g in failed_guardrails]}")

            # Add warning to content
            warnings = [f"⚠️ {v.guardrail_name}: {v.fail_reason}" for v in failed_guardrails]
            warning_message = "\n".join(warnings)
            modified_content = (
                f"[GUARDRAIL WARNING]\n{warning_message}\n\n" f"[Original Content - Use with Caution]\n{content}"
            )

        return AgentResult(
            content=modified_content,
            metadata={
                **result.metadata,
                "guardrails": {
                    "applied": True,
                    "all_passed": all_passed,
                    "results": [
                        {
                            "guardrail": v.guardrail_name,
                            "succeeded": v.succeeded,
                            "fail_reason": v.fail_reason,
                        }
                        for v in verification_results
                    ],
                },
            },
            tool_calls=result.tool_calls,
            history=result.history,
            usage=result.usage,
        )


class CustomPIIGuardrail(Guardrail):
    """
    Custom guardrail that detects PII (Personally Identifiable Information).

    This demonstrates creating a custom guardrail for specific use cases.
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """
        Initialize PII guardrail.

        Args:
            strict_mode: If True, be more aggressive in detecting potential PII
        """
        self.strict_mode = strict_mode

    async def verify(self, input_to_verify: str) -> GuardrailVerificationResult:
        """
        Verify input doesn't contain PII.

        Args:
            input_to_verify: Content to check for PII

        Returns:
            Verification result indicating if PII was detected
        """
        import re

        # Handle Prompt objects
        text = input_to_verify if isinstance(input_to_verify, str) else str(input_to_verify)

        # Define PII patterns
        patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        }

        if self.strict_mode:
            # Add more aggressive patterns in strict mode
            patterns["potential_name"] = r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"
            patterns["address_number"] = r"\b\d{1,5}\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd)\b"

        # Check for PII
        detected_pii = []
        for pii_type, pattern in patterns.items():
            if re.search(pattern, text):
                detected_pii.append(pii_type)

        succeeded = len(detected_pii) == 0
        fail_reason = None if succeeded else f"Detected PII: {', '.join(detected_pii)}"

        return GuardrailVerificationResult(
            guardrail_name="CustomPIIGuardrail",
            succeeded=succeeded,
            fail_reason=fail_reason,
        )


async def main() -> None:
    """Demonstrate guardrail post-processors with Ragbits GuardrailManager."""
    llm = LiteLLM("gpt-4o-mini")

    combined_guardrail = GuardrailPostProcessor(
        guardrails=[
            OpenAIModerationGuardrail(),
            CustomPIIGuardrail(strict_mode=False),
        ],
        fail_on_violation=False,
    )

    agent = Agent(
        llm=llm,
        prompt="You are a helpful assistant.",
        post_processors=[combined_guardrail],
    )

    prompt = (
        "Create a sample contact card with email john.doe@example.com and phone 555-123-4567. "
        "Add at the end 'I hate John!!!'"
    )
    result = await agent.run(prompt)

    print(f"Output: \n{result.content}")


if __name__ == "__main__":
    asyncio.run(main())
