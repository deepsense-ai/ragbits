import os
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel

from ragbits.guardrails.base import GuardrailManager, GuardrailVerificationResult
from ragbits.guardrails.openai_moderation import OpenAIModerationGuardrail


class MockedModeration(BaseModel):
    flagged: bool
    fail_reason: str | None


class MockedModerationCreateResponse(BaseModel):
    results: list[MockedModeration]


async def test_manager():
    guardrail_mock = AsyncMock()
    guardrail_mock.verify.return_value = GuardrailVerificationResult(
        guardrail_name=".", succeeded=True, fail_reason=None
    )
    manager = GuardrailManager([guardrail_mock])
    results = await manager.verify("test")
    assert guardrail_mock.verify.call_count == 1
    assert len(results) == 1


@patch.dict(os.environ, {"OPENAI_API_KEY": "."}, clear=True)
async def test_not_flagged():
    guardrail = OpenAIModerationGuardrail()
    guardrail._openai_client = AsyncMock()
    guardrail._openai_client.moderations.create.return_value = MockedModerationCreateResponse(
        results=[MockedModeration(flagged=False, fail_reason=None)]
    )
    results = await guardrail.verify("Test")
    assert results.succeeded is True
    assert results.fail_reason is None
    assert results.guardrail_name == "OpenAIModerationGuardrail"


@patch.dict(os.environ, {"OPENAI_API_KEY": "."}, clear=True)
async def test_flagged():
    guardrail = OpenAIModerationGuardrail()
    guardrail._openai_client = AsyncMock()
    guardrail._openai_client.moderations.create.return_value = MockedModerationCreateResponse(
        results=[MockedModeration(flagged=True, fail_reason="Harmful content")]
    )
    results = await guardrail.verify("Test")
    assert results.succeeded is False
    assert results.fail_reason == "[MockedModeration(flagged=True, fail_reason='Harmful content')]"
    assert results.guardrail_name == "OpenAIModerationGuardrail"
