import pytest
from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.post_processors.exceptions import (
    SupervisorCorrectionPromptFormatError,
    SupervisorMaxRetriesExceededError,
)
from ragbits.agents.post_processors.supervisor import (
    HistoryStrategy,
    SupervisorPostProcessor,
    ValidationInput,
    ValidationOutput,
)
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.core.prompt.prompt import Prompt


class AlwaysValidPrompt(Prompt[ValidationInput, ValidationOutput]):
    system_prompt = "You are a validator."
    user_prompt = "Validate last response."


class AlwaysInvalidPrompt(Prompt[ValidationInput, ValidationOutput]):
    system_prompt = "You are a validator."
    user_prompt = "Validate last response."


@pytest.fixture
def agent_llm() -> MockLLM:
    return MockLLM(default_options=MockLLMOptions(response="Agent answer"))


@pytest.mark.asyncio
async def test_supervisor_accepts_valid_response_and_attaches_metadata(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="System prompt for agent")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(response='{"is_valid": true, "reasoning": "ok", "suggestion": ""}')
    )

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=AlwaysValidPrompt,
        max_retries=2,
    )

    result = await agent.run("What is the weather in Tokyo?", post_processors=[supervisor])

    assert result.content == "Agent answer"
    assert "post_processors" in result.metadata
    assert "supervisor" in result.metadata["post_processors"]

    validations = result.metadata["post_processors"]["supervisor"]
    assert isinstance(validations, list)
    assert len(validations) == 1
    assert validations[0]["is_valid"] is True


@pytest.mark.asyncio
async def test_supervisor_returns_after_retry_limit_when_fail_on_exceed_false(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="System prompt for agent")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(response='{"is_valid": false, "reasoning": "bad", "suggestion": "fix"}')
    )

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=AlwaysInvalidPrompt,
        max_retries=2,
        fail_on_exceed=False,
        history_strategy=HistoryStrategy.REMOVE,
    )

    result = await agent.run("Q?", post_processors=[supervisor])

    assert "post_processors" in result.metadata
    validations = result.metadata["post_processors"]["supervisor"]
    assert isinstance(validations, list)
    assert len(validations) == 3
    assert all(v["is_valid"] is False for v in validations)


@pytest.mark.asyncio
async def test_supervisor_raises_after_retry_limit_when_fail_on_exceed_true(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="System prompt for agent")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(response='{"is_valid": false, "reasoning": "bad", "suggestion": "fix"}')
    )

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=AlwaysInvalidPrompt,
        max_retries=2,
        fail_on_exceed=True,
    )

    with pytest.raises(SupervisorMaxRetriesExceededError) as exc:
        await agent.run("Q?", post_processors=[supervisor])

    err = exc.value
    assert err.max_retries == 2
    assert len(err.last_validations) == 3
    assert all(v.is_valid is False for v in err.last_validations)


@pytest.mark.asyncio
async def test_supervisor_history_remove_prunes_invalid_and_correction_user(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="System prompt for agent")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(response='{"is_valid": false, "reasoning": "bad", "suggestion": "fix"}')
    )

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=AlwaysInvalidPrompt,
        max_retries=1,
        fail_on_exceed=False,
        history_strategy=HistoryStrategy.REMOVE,
    )

    result = await agent.run("Q?", post_processors=[supervisor])

    history = result.history
    assert len(history) == 3
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[1]["content"] == "Q?"
    assert history[2]["role"] == "assistant"
    assert history[2]["content"] == "Agent answer"


@pytest.mark.asyncio
async def test_supervisor_history_preserve_keeps_invalid_and_correction_user(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="System prompt for agent")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(response='{"is_valid": false, "reasoning": "bad", "suggestion": "fix"}')
    )

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=AlwaysInvalidPrompt,
        max_retries=1,
        fail_on_exceed=False,
        history_strategy=HistoryStrategy.PRESERVE,
    )

    result = await agent.run("Q?", post_processors=[supervisor])

    history = result.history
    assert len(history) == 5
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[1]["content"] == "Q?"
    assert history[2]["role"] == "assistant"
    assert history[2]["content"] == "Agent answer"
    assert history[3]["role"] == "user"
    assert isinstance(history[3]["content"], str)
    assert "Your answer is incorrect" in history[3]["content"]
    assert history[4]["role"] == "assistant"
    assert history[4]["content"] == "Agent answer"


class MyValidationOutput(BaseModel):
    is_valid: bool
    errors: list[str]
    fixes: list[str]
    confidence: float


class MyValidationPrompt(Prompt[ValidationInput, MyValidationOutput]):
    system_prompt = "Mocked system prompt"
    user_prompt = "Mocked user prompt"


@pytest.mark.asyncio
async def test_supervisor_custom_validation_and_correction_prompt_preserve_history(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="You are a professional weather reporter.")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(
            response=(
                '{"is_valid": false, "errors": ["not detailed enough"], '
                '"fixes": ["add more details"], "confidence": 0.9}'
            )
        )
    )

    correction_prompt = (
        "Previous answer had issues:\n"
        "Errors: {errors}\n"
        "Fixes: {fixes}\n"
        "Confidence: {confidence}\n"
        "Please answer again using the fixes."
    )

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=MyValidationPrompt,
        correction_prompt=correction_prompt,
        max_retries=1,
        fail_on_exceed=False,
        history_strategy=HistoryStrategy.PRESERVE,
    )

    result = await agent.run("What is the weather in Tokyo?", post_processors=[supervisor])

    validations = result.metadata["post_processors"]["supervisor"]
    assert isinstance(validations, list)
    assert len(validations) == 2
    assert all("errors" in v and "fixes" in v and v["is_valid"] is False for v in validations)

    history = result.history
    assert len(history) == 5
    assert history[0]["role"] == "system"
    assert history[0]["content"]
    assert history[1]["role"] == "user"
    assert history[1]["content"]
    assert history[2]["role"] == "assistant"
    assert history[3]["role"] == "user"
    assert history[3]["content"]

    corr = history[3]["content"]
    assert "Previous answer had issues:" in corr
    assert "Errors:" in corr
    assert "not detailed enough" in corr
    assert "Fixes:" in corr
    assert "add more details" in corr
    assert "Confidence: 0.9" in corr
    assert history[4]["role"] == "assistant"


@pytest.mark.asyncio
async def test_supervisor_raises_when_correction_prompt_has_missing_fields(agent_llm: MockLLM) -> None:
    agent: Agent = Agent(llm=agent_llm, prompt="System prompt for agent")

    validation_llm = MockLLM(
        default_options=MockLLMOptions(response='{"is_valid": false, "reasoning": "bad", "suggestion": "fix"}')
    )

    bad_correction_prompt = "Missing field here: {nonexistent}"

    supervisor: SupervisorPostProcessor = SupervisorPostProcessor(
        llm=validation_llm,
        validation_prompt=AlwaysInvalidPrompt,
        correction_prompt=bad_correction_prompt,
        max_retries=1,
        fail_on_exceed=False,
        history_strategy=HistoryStrategy.PRESERVE,
    )

    with pytest.raises(SupervisorCorrectionPromptFormatError) as exc:
        await agent.run("Q?", post_processors=[supervisor])

    err = exc.value
    msg = str(err)
    assert "failed to format correction prompt" in msg.lower()
    assert "nonexistent" in msg.lower()
    assert err.missing_keys == ["nonexistent"]
