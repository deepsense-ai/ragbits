from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from ragbits.agents.post_processors.base import PostProcessor
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentResult


class ValidationOutput(BaseModel):
    """Default result of the validation process."""

    is_valid: bool
    """Whether the response is valid based on tool calls."""
    reasoning: str
    """Explanation of the validation decision."""
    suggestion: str
    """Suggestion for correction."""


class ValidationInput(BaseModel):
    """Input data for validation prompt."""

    chat_history: list[dict[str, Any]]
    """The complete chat history for context."""


class DefaultSupervisorPrompt(Prompt[ValidationInput, ValidationOutput]):
    """
    Default prompt for validating agent responses against tool call results.
    """

    system_prompt = """
    You are an expert validator that analyzes whether an AI agent's response is logically consistent
    with the tool calls it executed and their results. Your job is to determine if the response
    could reasonably be generated based on the available information from the tools.

    Analyze the following:
    1. Whether the response content is supported by the tool call results
    2. If any claims in the response contradict the tool data
    3. If the response makes assumptions not supported by the tool results
    4. Whether the response appropriately handles cases where tools failed or returned no data
    5. Whether the response actually answers the user's question
    6. Whether the response is factually correct based on available evidence

    IMPORTANT VALIDATION RULES:
    - Only flag as INVALID if the answer is clearly incorrect or contradicts the tool results
    - If the answer cannot be determined to be true because it's basic/common knowledge not covered by tools,
    consider it as VALID
    - If the response doesn't directly answer the user's question, flag as INVALID
    - Be strict but fair - flag clear inconsistencies while allowing for reasonable inference
      and interpretation of the tool results
    """

    user_prompt = """
    Chat History:
    {% for message in chat_history %}
    {{ message.role | title }}: {% if message.content is none %}{% for tool_call in message.tool_calls %} called tool:
        {{ tool_call.function.name }}({{ tool_call.function.arguments | tojson }}){% if not loop.last %} {% endif %}{% endfor %}{% else %}{{ message.content }}{% endif %}
    {% endfor %}

    Please validate whether the last agent's response is logically consistent with the tool call results
    and the conversation context.
    """


DEFAULT_CORRECTION_PROMPT = """
Your answer is incorrect. Below you will find the reasoning and suggestion for correction.
Reasoning: {reasoning}
Suggestion: {suggestion}
Please answer again, considering the reasoning and suggestion.
"""


class SupervisorPostProcessor(PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """
    Post-processor that validates agent responses against executed tool calls.

    This supervisor uses an LLM to analyze whether the agent's final response
    is logically consistent with the results of the tool calls it executed.
    """

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        validation_prompt: type[Prompt[BaseModel, BaseModel]] | None = None,
        correction_prompt: str | None = None,
        max_retries: int = 3,
        fail_on_exceed: bool = False,
    ) -> None:
        self.llm = llm
        self.validation_prompt = validation_prompt or DefaultSupervisorPrompt
        self.correction_prompt = correction_prompt or DEFAULT_CORRECTION_PROMPT
        self.max_retries = max_retries
        self.fail_on_exceed = fail_on_exceed

    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
    ) -> "AgentResult[PromptOutputT]":
        retries = 0
        current_result = result
        validations: list[BaseModel] = []

        print("\n[DEBUG] Result content before malforming to error: ", current_result.history[-1]["content"])
        current_result.history[-1]["content"] = "The weather is currently cloudy."
        print("\n[DEBUG] Result content after malforming to error: ", current_result.history[-1]["content"])

        while retries <= self.max_retries:
            validation = await self._validate(current_result)
            print("\n[SupervisorPostProcessor] Validation response: ", validation)
            validations.append(validation)

            if validation.is_valid:
                return self._attach_metadata(current_result, validations)

            if retries == self.max_retries:
                if self.fail_on_exceed:
                    raise RuntimeError("Supervisor: maximum retries exceeded")  # TODO: add custom exception
                return self._attach_metadata(current_result, validations)

            current_result = await self._rerun(agent, current_result, validation)
            retries += 1

        return self._attach_metadata(current_result, validations)

    async def _validate(self, result: "AgentResult") -> BaseModel:
        input_data = self._build_validation_input(result)
        prompt = self.validation_prompt(input_data)

        print("--------------------------------")
        print(prompt.rendered_user_prompt)
        print("--------------------------------")

        return await self.llm.generate(prompt)

    def _build_validation_input(self, result: "AgentResult") -> ValidationInput:
        return ValidationInput(
            chat_history=result.history,
        )

    async def _rerun(
        self,
        agent: "Agent",
        result: "AgentResult",
        validation: BaseModel,
    ) -> "AgentResult":
        # TODO: add try catch for correction prompts that use arguments unset in validation
        correction_prompt = self.correction_prompt.format(**validation.model_dump())

        # TODO: re-run with full snapshot of original options
        return await agent._run_without_post_processing(correction_prompt)

    def _attach_metadata(
        self,
        result: "AgentResult",
        validations: list[BaseModel],
    ) -> "AgentResult":
        result.metadata.setdefault("post_processors", {}).setdefault("supervisor", []).extend(
            [v.model_dump() for v in validations]
        )
        return result
