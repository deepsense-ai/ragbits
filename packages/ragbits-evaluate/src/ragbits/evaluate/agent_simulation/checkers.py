"""Task completion checkers for agent simulation scenarios."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import BaseModel, Field

from ragbits.core.prompt import Prompt

if TYPE_CHECKING:
    from ragbits.agents.tool import ToolCallResult
    from ragbits.evaluate.agent_simulation.models import Task, Turn


class LLMCheckerPromptInput(BaseModel):
    """Input for the LLM checker prompt."""

    task: str
    expected_result: str
    context_block: str
    history_block: str


class LLMCheckerPromptOutput(BaseModel):
    """Output schema for the LLM checker prompt."""

    done: bool = Field(..., description="Whether the task has been completed")
    reason: str = Field(..., description="Short explanation of the decision")


class LLMCheckerPrompt(Prompt[LLMCheckerPromptInput, LLMCheckerPromptOutput]):
    """Prompt for LLM-based task completion checking."""

    system_prompt = """
You are a strict task-completion judge for a user-assistant conversation.
Decide if the assistant has fulfilled the current task.
Current task: {{ task }}
Expected result: {{ expected_result }}
{{ context_block }}
"""

    user_prompt = """
[CONVERSATION]
{{ history_block }}

[TASK]
Evaluate if the task has been completed and provide your decision.
"""


class CheckerResult(BaseModel):
    """Standard response schema for all checkers."""

    completed: bool = Field(..., description="Whether the task/turn check passed")
    reason: str = Field(..., description="Human-readable explanation of the decision")
    checker_type: str = Field(..., description="Type of checker that produced this result")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional checker-specific details")


class BaseCheckerConfig(BaseModel, ABC):
    """Base configuration for all checkers. Subclass this to create new checker types."""

    type: ClassVar[str]  # Each subclass must define this

    @abstractmethod
    async def check(
        self,
        task: Task,
        history: list[Turn],
        tool_calls: list[ToolCallResult],
        state: dict[str, Any],
        context: CheckerContext,
    ) -> CheckerResult:
        """Run the check and return result.

        Args:
            task: The current task being checked.
            history: List of conversation turns so far.
            tool_calls: List of tool calls made in the current turn.
            state: Current conversation state.
            context: Shared context with LLM and other resources.

        Returns:
            CheckerResult with the decision and reasoning.
        """


class CheckerContext(BaseModel):
    """Shared context passed to all checkers during evaluation."""

    model_config = {"arbitrary_types_allowed": True}

    llm: Any = Field(default=None, description="LLM instance for checkers that need it")
    domain_context: Any = Field(default=None, description="Optional domain context")


# =============================================================================
# Checker Registry
# =============================================================================

_CHECKER_REGISTRY: dict[str, type[BaseCheckerConfig]] = {}


def register_checker(checker_type: str) -> Callable[[type[BaseCheckerConfig]], type[BaseCheckerConfig]]:
    """Decorator to register a checker type.

    Usage:
        @register_checker("my_checker")
        class MyCheckerConfig(BaseCheckerConfig):
            type: ClassVar[str] = "my_checker"
            ...
    """

    def decorator(cls: type[BaseCheckerConfig]) -> type[BaseCheckerConfig]:
        cls.type = checker_type
        _CHECKER_REGISTRY[checker_type] = cls
        return cls

    return decorator


def get_checker_class(checker_type: str) -> type[BaseCheckerConfig]:
    """Get a checker class by type name."""
    if checker_type not in _CHECKER_REGISTRY:
        available = ", ".join(_CHECKER_REGISTRY.keys())
        raise ValueError(f"Unknown checker type: {checker_type}. Available: {available}")
    return _CHECKER_REGISTRY[checker_type]


def list_checker_types() -> list[str]:
    """List all registered checker types."""
    return list(_CHECKER_REGISTRY.keys())


def parse_checker_config(data: dict[str, Any]) -> BaseCheckerConfig:
    """Parse a checker config dict into the appropriate typed config.

    Args:
        data: Dict with "type" key and checker-specific fields.

    Returns:
        Typed checker config instance.
    """
    checker_type = data.get("type")
    if not checker_type:
        raise ValueError("Checker config must have a 'type' field")

    checker_class = get_checker_class(checker_type)
    return checker_class(**{k: v for k, v in data.items() if k != "type"})


# =============================================================================
# Built-in Checkers
# =============================================================================


@register_checker("llm")
class LLMCheckerConfig(BaseCheckerConfig):
    """LLM-based checker that uses a language model to evaluate task completion."""

    type: ClassVar[str] = "llm"

    expected_result: str = Field(..., description="Description of the expected outcome")

    async def check(
        self,
        task: Task,
        history: list[Turn],
        tool_calls: list[ToolCallResult],
        state: dict[str, Any],
        context: CheckerContext,
    ) -> CheckerResult:
        """Check task completion using LLM evaluation."""
        if context.llm is None:
            return CheckerResult(
                completed=False,
                reason="LLM checker requires an LLM instance but none was provided",
                checker_type=self.type,
            )

        prompt = LLMCheckerPrompt(
            LLMCheckerPromptInput(
                task=task.task,
                expected_result=self.expected_result,
                context_block=self._build_context_block(context),
                history_block=self._build_history_block(history),
            )
        )

        response: LLMCheckerPromptOutput = await context.llm.generate(prompt)

        return CheckerResult(
            completed=response.done,
            reason=response.reason,
            checker_type=self.type,
            details={"expected_result": self.expected_result},
        )

    @staticmethod
    def _build_context_block(context: CheckerContext) -> str:
        """Build the domain context block string."""
        if context.domain_context:
            return (
                "\n[IMPORTANT CONTEXT]\n"
                f"{context.domain_context.format_for_prompt()}\n\n"
                "When evaluating task completion, consider the domain context above "
                f"and use {context.domain_context.locale} locale conventions.\n"
            )
        return ""

    @staticmethod
    def _build_history_block(history: list[Turn]) -> str:
        """Build the conversation history block string."""
        if not history:
            return "(no prior messages)"
        history_text = [f"User: {t.user}\nAssistant: {t.assistant}" for t in history]
        return "\n\n".join(history_text)


class ToolCallExpectation(BaseModel):
    """Expected tool call specification."""

    name: str = Field(..., description="Name of the tool that should be called")
    arguments: dict[str, Any] | None = Field(
        default=None,
        description="Optional arguments that should match (partial match)",
    )
    result_contains: str | None = Field(
        default=None,
        description="Optional string that should be present in the tool result",
    )


@register_checker("tool_call")
class ToolCallCheckerConfig(BaseCheckerConfig):
    """Checker that verifies specific tool calls were made."""

    type: ClassVar[str] = "tool_call"

    tools: list[ToolCallExpectation | str] = Field(
        ..., description="Expected tools - can be names or detailed expectations"
    )
    mode: Literal["all", "any"] = Field(
        default="all", description="'all' requires all tools, 'any' requires at least one"
    )

    async def check(  # noqa: PLR0912
        self,
        task: Task,
        history: list[Turn],
        tool_calls: list[ToolCallResult],
        state: dict[str, Any],
        context: CheckerContext,
    ) -> CheckerResult:
        """Check if expected tool calls were made."""
        if not self.tools:
            return CheckerResult(
                completed=True,
                reason="No expected tools specified",
                checker_type=self.type,
            )

        if not tool_calls:
            return CheckerResult(
                completed=False,
                reason="No tools were called, but tools were expected",
                checker_type=self.type,
                details={"expected": [t if isinstance(t, str) else t.name for t in self.tools], "called": []},
            )

        # Normalize expectations
        expectations: list[ToolCallExpectation] = []
        for tool in self.tools:
            if isinstance(tool, str):
                expectations.append(ToolCallExpectation(name=tool))
            else:
                expectations.append(tool)

        matched_tools: list[str] = []
        unmatched_tools: list[str] = []
        match_details: dict[str, dict[str, Any]] = {}

        for expected in expectations:
            found = False
            for call in tool_calls:
                if call.name != expected.name:
                    continue

                # Check arguments if specified
                if expected.arguments:
                    args_match = all(call.arguments.get(k) == v for k, v in expected.arguments.items())
                    if not args_match:
                        match_details[expected.name] = {
                            "status": "args_mismatch",
                            "expected_args": expected.arguments,
                            "actual_args": call.arguments,
                        }
                        continue

                # Check result contains if specified
                if expected.result_contains:
                    result_str = str(call.result) if call.result else ""
                    if expected.result_contains not in result_str:
                        match_details[expected.name] = {
                            "status": "result_mismatch",
                            "expected_contains": expected.result_contains,
                            "actual_result": result_str[:200],
                        }
                        continue

                found = True
                matched_tools.append(expected.name)
                match_details[expected.name] = {"status": "matched"}
                break

            if not found and expected.name not in match_details:
                unmatched_tools.append(expected.name)
                match_details[expected.name] = {"status": "not_called"}

        called_names = [tc.name for tc in tool_calls]

        if self.mode == "all":
            completed = len(unmatched_tools) == 0 and all(
                d.get("status") == "matched" for d in match_details.values()
            )
            if completed:
                reason = f"All expected tools matched: {', '.join(matched_tools)}"
            else:
                failed = [k for k, v in match_details.items() if v.get("status") != "matched"]
                reason = f"Tool check failed for: {', '.join(failed)}. Called: {', '.join(called_names)}"
        else:  # mode == "any"
            completed = len(matched_tools) > 0
            if completed:
                reason = f"Found matching tool(s): {', '.join(matched_tools)}"
            else:
                reason = f"None of expected tools matched. Expected: {', '.join(e.name for e in expectations)}"

        return CheckerResult(
            completed=completed,
            reason=reason,
            checker_type=self.type,
            details={
                "matched": matched_tools,
                "unmatched": unmatched_tools,
                "called": called_names,
                "match_details": match_details,
            },
        )


class StateExpectation(BaseModel):
    """Expected state value specification."""

    key: str = Field(..., description="Key path in state (supports dot notation like 'user.name')")
    value: Any | None = Field(default=None, description="Expected exact value")
    exists: bool | None = Field(default=None, description="Check existence (True) or non-existence (False)")
    contains: str | None = Field(default=None, description="For strings, check if contains this substring")
    min_value: float | None = Field(default=None, description="For numbers, minimum allowed value")
    max_value: float | None = Field(default=None, description="For numbers, maximum allowed value")


@register_checker("state")
class StateCheckerConfig(BaseCheckerConfig):
    """Checker that verifies state has specific values."""

    type: ClassVar[str] = "state"

    checks: list[StateExpectation] = Field(..., description="State conditions to verify")
    mode: Literal["all", "any"] = Field(
        default="all", description="'all' requires all checks, 'any' requires at least one"
    )

    def _get_nested_value(self, state: dict[str, Any], key_path: str) -> tuple[bool, Any]:  # noqa: PLR6301
        """Get a nested value from state using dot notation."""
        keys = key_path.split(".")
        current = state
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False, None
        return True, current

    async def check(  # noqa: PLR0912, PLR0915
        self,
        task: Task,
        history: list[Turn],
        tool_calls: list[ToolCallResult],
        state: dict[str, Any],
        context: CheckerContext,
    ) -> CheckerResult:
        """Check if state meets the specified criteria."""
        if not self.checks:
            return CheckerResult(
                completed=True,
                reason="No state checks specified",
                checker_type=self.type,
            )

        passed_checks: list[str] = []
        failed_checks: list[str] = []
        check_details: dict[str, dict[str, Any]] = {}

        for check in self.checks:
            exists, value = self._get_nested_value(state, check.key)

            # Check existence
            if check.exists is not None:
                if check.exists and not exists:
                    failed_checks.append(check.key)
                    check_details[check.key] = {"status": "not_exists", "expected": "exists"}
                    continue
                elif not check.exists and exists:
                    failed_checks.append(check.key)
                    check_details[check.key] = {"status": "exists", "expected": "not_exists"}
                    continue

            if not exists and check.exists is None:
                failed_checks.append(check.key)
                check_details[check.key] = {"status": "not_exists"}
                continue

            # Check exact value
            if check.value is not None and value != check.value:
                failed_checks.append(check.key)
                check_details[check.key] = {
                    "status": "value_mismatch",
                    "expected": check.value,
                    "actual": value,
                }
                continue

            # Check contains (for strings)
            if check.contains is not None:  # noqa: SIM102
                if not isinstance(value, str) or check.contains not in value:
                    failed_checks.append(check.key)
                    check_details[check.key] = {
                        "status": "contains_failed",
                        "expected_contains": check.contains,
                        "actual": str(value)[:200],
                    }
                    continue

            # Check min/max value (for numbers)
            if check.min_value is not None:
                try:
                    if float(value) < check.min_value:
                        failed_checks.append(check.key)
                        check_details[check.key] = {
                            "status": "below_min",
                            "min": check.min_value,
                            "actual": value,
                        }
                        continue
                except (ValueError, TypeError):
                    failed_checks.append(check.key)
                    check_details[check.key] = {"status": "not_numeric", "actual": value}
                    continue

            if check.max_value is not None:
                try:
                    if float(value) > check.max_value:
                        failed_checks.append(check.key)
                        check_details[check.key] = {
                            "status": "above_max",
                            "max": check.max_value,
                            "actual": value,
                        }
                        continue
                except (ValueError, TypeError):
                    failed_checks.append(check.key)
                    check_details[check.key] = {"status": "not_numeric", "actual": value}
                    continue

            passed_checks.append(check.key)
            check_details[check.key] = {"status": "passed", "value": value}

        if self.mode == "all":
            completed = len(failed_checks) == 0
            if completed:
                reason = f"All state checks passed: {', '.join(passed_checks)}"
            else:
                reason = f"State checks failed: {', '.join(failed_checks)}"
        else:  # mode == "any"
            completed = len(passed_checks) > 0
            if completed:  # noqa: SIM108
                reason = f"State check(s) passed: {', '.join(passed_checks)}"
            else:
                reason = "No state checks passed"

        return CheckerResult(
            completed=completed,
            reason=reason,
            checker_type=self.type,
            details={
                "passed": passed_checks,
                "failed": failed_checks,
                "check_details": check_details,
                "current_state": state,
            },
        )


# =============================================================================
# Checker Runner
# =============================================================================


async def run_checkers(
    checkers: list[BaseCheckerConfig],
    task: Task,
    history: list[Turn],
    tool_calls: list[ToolCallResult],
    state: dict[str, Any],
    context: CheckerContext,
    mode: Literal["all", "any"] = "all",
) -> CheckerResult:
    """Run multiple checkers and combine results.

    Args:
        checkers: List of checker configs to run.
        task: The current task.
        history: Conversation history.
        tool_calls: Tool calls from current turn.
        state: Current state.
        context: Shared checker context.
        mode: 'all' requires all to pass, 'any' requires at least one.

    Returns:
        Combined CheckerResult.
    """
    if not checkers:
        return CheckerResult(
            completed=False,
            reason="No checkers configured",
            checker_type="none",
        )

    results: list[CheckerResult] = []
    for checker in checkers:
        result = await checker.check(task, history, tool_calls, state, context)
        results.append(result)

        if mode == "any" and result.completed:
            return CheckerResult(
                completed=True,
                reason=f"[{result.checker_type}] {result.reason}",
                checker_type=result.checker_type,
                details={
                    "mode": mode,
                    "passed_checker": result.checker_type,
                    "all_results": [r.model_dump() for r in results],
                },
            )
        elif mode == "all" and not result.completed:
            return CheckerResult(
                completed=False,
                reason=f"[{result.checker_type}] {result.reason}",
                checker_type=result.checker_type,
                details={
                    "mode": mode,
                    "failed_checker": result.checker_type,
                    "all_results": [r.model_dump() for r in results],
                },
            )

    # All passed (for "all" mode) or none passed (for "any" mode)
    checker_types = [r.checker_type for r in results]
    if mode == "all":
        return CheckerResult(
            completed=True,
            reason=f"All {len(results)} checkers passed: {', '.join(checker_types)}",
            checker_type="combined",
            details={
                "mode": mode,
                "checkers": checker_types,
                "all_results": [r.model_dump() for r in results],
            },
        )
    else:  # mode == "any" and none passed
        return CheckerResult(
            completed=False,
            reason=f"None of {len(results)} checkers passed: {', '.join(checker_types)}",
            checker_type="combined",
            details={
                "mode": mode,
                "checkers": checker_types,
                "all_results": [r.model_dump() for r in results],
            },
        )
