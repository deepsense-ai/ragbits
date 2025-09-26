from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Optional, Protocol, TypeVar, cast

from pydantic import BaseModel

from ragbits.agents.post_processors.base import PostProcessor
from ragbits.agents.post_processors.exceptions import (
    SupervisorCorrectionPromptFormatError,
    SupervisorMaxRetriesExceededError,
)
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.prompt.prompt import ChatFormat, Prompt, PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentOptions, AgentResult, AgentRunContext


class HistoryStrategy(str, Enum):
    """Strategy for handling the chat history."""

    PRESERVE = "preserve"
    REMOVE = "remove"


class SupportsValidation(Protocol):
    """Protocol for post-processors that support validation."""

    is_valid: bool

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Return a dict of model fields (compatible with BaseModel.model_dump)."""
        ...


ValidationOutputT = TypeVar("ValidationOutputT", bound=SupportsValidation)


class ValidationOutput(BaseModel):
    """Result of the validation process for agent responses."""

    is_valid: bool
    """Whether the response is valid based on tool calls."""

    reasoning: str
    """Explanation of the validation decision."""

    suggestion: str
    """Suggestion for correction."""


class ValidationInput(BaseModel):
    """Input data for the validation prompt."""

    chat_history: ChatFormat
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

    user_prompt = (
        "Chat History:\n"
        "{% for message in chat_history %}\n"
        "{{ message.role | title }}: "
        "{% if message.content is none %}"
        "{% for tool_call in message.tool_calls %}"
        "called tool: "
        "{{ tool_call.function.name }}({{ tool_call.function.arguments | tojson }})"
        "{% if not loop.last %} {% endif %}"
        "{% endfor %}"
        "{% else %}{{ message.content }}{% endif %}"
        "{% endfor %}\n"
        "\nPlease validate whether the last assistant's response is logically consistent with the tool call results "
        "and the conversation context."
    )


DEFAULT_CORRECTION_PROMPT = (
    "Your answer is incorrect. Below you will find the reasoning and suggestion for correction.\n"
    "Reasoning: {reasoning}\n"
    "Suggestion: {suggestion}\n"
    "Please answer again, considering the reasoning and suggestion.\n"
)


class SupervisorPostProcessor(
    PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT],
    Generic[LLMClientOptionsT, PromptInputT, ValidationOutputT, PromptOutputT],
):
    """
    Post-processor that validates agent responses against executed tool calls.

    This supervisor uses an LLM to analyze whether the agent's final response
    is logically consistent with the results of the tool calls it executed.
    """

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        validation_prompt: type[Prompt[ValidationInput, ValidationOutputT]] | None = None,
        correction_prompt: str | None = None,
        max_retries: int = 3,
        fail_on_exceed: bool = True,
        history_strategy: HistoryStrategy = HistoryStrategy.REMOVE,
    ) -> None:
        self.llm = llm
        self.validation_prompt: type[Prompt[ValidationInput, ValidationOutputT]] = cast(
            type[Prompt[ValidationInput, ValidationOutputT]],
            validation_prompt or DefaultSupervisorPrompt,
        )
        self.correction_prompt = correction_prompt or DEFAULT_CORRECTION_PROMPT
        self.max_retries = max_retries
        self.fail_on_exceed = fail_on_exceed
        self.history_strategy = history_strategy

    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        options: Optional["AgentOptions[LLMClientOptionsT]"] = None,
        context: Optional["AgentRunContext"] = None,
    ) -> "AgentResult[PromptOutputT]":
        """
        Validate the agent's response and, if necessary, rerun with corrections.
        """
        retries = 0
        current_result = result
        validations: list[ValidationOutputT] = []
        accumulated_tool_calls: list = []
        agent.history = result.history

        while retries <= self.max_retries:
            validation = await self._validate(current_result)
            validations.append(validation)
            accumulated_tool_calls.extend(current_result.tool_calls or [])
            current_result.tool_calls = accumulated_tool_calls

            if validation.is_valid:
                if not agent.keep_history:
                    agent.history = []
                return self._attach_metadata(current_result, validations)

            if retries == self.max_retries:
                if self.fail_on_exceed:
                    raise SupervisorMaxRetriesExceededError(self.max_retries, validations)
                if not agent.keep_history:
                    agent.history = []
                return self._attach_metadata(current_result, validations)

            last_assistant_index = len(current_result.history) - 1
            current_result = await self._rerun(agent, validation, options, context)
            current_result = self._handle_history(current_result, last_assistant_index)
            retries += 1

        if not agent.keep_history:
            agent.history = []
        return self._attach_metadata(current_result, validations)

    async def _validate(self, result: "AgentResult[PromptOutputT]") -> ValidationOutputT:
        """
        Run the validation prompt on the agent result.
        """
        input_data = ValidationInput(chat_history=result.history)
        prompt = self.validation_prompt(input_data)
        return await self.llm.generate(prompt)

    async def _rerun(
        self,
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        validation: ValidationOutputT,
        options: Optional["AgentOptions[LLMClientOptionsT]"] = None,
        context: Optional["AgentRunContext"] = None,
    ) -> "AgentResult[PromptOutputT]":
        """
        Rerun the agent with a correction prompt based on validation feedback.
        """
        try:
            correction_prompt = self.correction_prompt.format(**validation.model_dump())
        except KeyError as exc:
            missing = [str(exc).strip("'\"")]
            raise SupervisorCorrectionPromptFormatError(missing_keys=missing, original_error=exc) from exc
        except Exception as exc:
            raise SupervisorCorrectionPromptFormatError(original_error=exc) from exc

        return await agent._run_without_post_processing(correction_prompt, options, context)

    @staticmethod
    def _attach_metadata(
        result: "AgentResult[PromptOutputT]",
        validations: list[ValidationOutputT],
    ) -> "AgentResult[PromptOutputT]":
        """
        Attach validation metadata to the agent result.
        """
        result.metadata.setdefault("post_processors", {}).setdefault("supervisor", []).extend(
            [v.model_dump() for v in validations]
        )
        return result

    def _handle_history(
        self,
        result: "AgentResult[PromptOutputT]",
        last_assistant_index: int,
    ) -> "AgentResult[PromptOutputT]":
        """
        Handle the chat history according to the configured strategy.
        """
        if self.history_strategy == HistoryStrategy.REMOVE:
            result.history.pop(last_assistant_index + 1)
            result.history.pop(last_assistant_index)

        return result
