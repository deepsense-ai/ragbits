from unittest.mock import MagicMock, patch

import pytest
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BatchEncoding

from ragbits.core.llms.local import LocalLLM, LocalLLMOptions
from ragbits.core.prompt.base import SimplePrompt

INPUT_VALUE = 1
PADDING_VALUE = 0


@pytest.fixture
def mock_model():
    """Fixture to create a mock model."""
    model = MagicMock(spec=AutoModelForCausalLM)
    model.device = "cpu"

    def _generate(input_ids: torch.Tensor, **kwargs) -> torch.Tensor:
        output = []
        n_rows = input_ids.shape[0]
        for idx in range(1, input_ids.shape[0] + 1):
            output.append(input_ids[idx - 1].tolist() + [INPUT_VALUE] * idx + [PADDING_VALUE] * (n_rows - idx))
        return torch.tensor(output)

    model.generate = MagicMock(side_effect=_generate)
    return model


@pytest.fixture
def mock_tokenizer():
    """Fixture to create a mock tokenizer."""
    tokenizer = MagicMock(spec=AutoTokenizer)
    tokenizer.eos_token_id = 2
    tokenizer._pad_token_type_id = PADDING_VALUE

    def _apply_chat_template(template: list[dict], **kwargs) -> dict[str, torch.Tensor]:
        output: dict[str, list[list[int]]] = {"input_ids": [], "attention_mask": []}
        n_rows = len(template)
        for idx in range(1, n_rows + 1):
            output["input_ids"].append([INPUT_VALUE] * idx + [PADDING_VALUE] * (n_rows - idx))
            output["attention_mask"].append([1] * idx + [0] * (n_rows - idx))
        return BatchEncoding(
            {"input_ids": torch.tensor(output["input_ids"]), "attention_mask": torch.tensor(output["attention_mask"])}
        )

    tokenizer.apply_chat_template = MagicMock(side_effect=_apply_chat_template)
    tokenizer.get_chat_template = MagicMock()

    def _decode(input_ids: torch.Tensor, **kwargs) -> list[str]:
        return ["VAL" if val == INPUT_VALUE else "PAD" for val in input_ids.tolist()]

    tokenizer.decode = MagicMock(side_effect=_decode)
    return tokenizer


@pytest.fixture
def local_llm(mock_model: MagicMock, mock_tokenizer: MagicMock):
    """Fixture to create a LocalLLM instance with mocked dependencies."""
    with (
        patch("ragbits.core.llms.local.AutoModelForCausalLM.from_pretrained", return_value=mock_model),
        patch("ragbits.core.llms.local.AutoTokenizer.from_pretrained", return_value=mock_tokenizer),
    ):
        llm = LocalLLM(model_name="test-model")
        return llm


async def test_call_with_tools(local_llm: LocalLLM):
    """Test that _call raises NotImplementedError when tools are provided."""
    prompt = [SimplePrompt("Prompt1")]
    options = LocalLLMOptions(temperature=0.7)
    tools = [{"name": "test_tool"}]

    with pytest.raises(NotImplementedError, match="Tools are not supported for local LLMs"):
        await local_llm._call(prompt, options, tools=tools)


async def test_call(local_llm: LocalLLM):
    """Test the _call method."""
    prompt = [SimplePrompt("Prompt1"), SimplePrompt("Prompt2"), SimplePrompt("Prompt3")]
    options = LocalLLMOptions(temperature=0.7)

    result = await local_llm._call(prompt, options)

    assert local_llm.model.generate.call_args.kwargs["eos_token_id"] == local_llm.tokenizer.eos_token_id
    assert local_llm.model.generate.call_args.kwargs["temperature"] == options.temperature

    assert len(result) == 3
    assert result[0]["response"] == ["VAL", "PAD", "PAD"]
    assert result[0]["reasoning"] is None
    assert result[0]["usage"]["prompt_tokens"] == 1
    assert result[0]["usage"]["completion_tokens"] == 1
    assert result[0]["usage"]["total_tokens"] == 2
    assert "throughput" in result[0]

    assert result[1]["response"] == ["VAL", "VAL", "PAD"]
    assert result[1]["reasoning"] is None
    assert result[1]["usage"]["prompt_tokens"] == 2
    assert result[1]["usage"]["completion_tokens"] == 2
    assert result[1]["usage"]["total_tokens"] == 4
    assert "throughput" in result[1]

    assert result[2]["response"] == ["VAL", "VAL", "VAL"]
    assert result[2]["reasoning"] is None
    assert result[2]["usage"]["prompt_tokens"] == 3
    assert result[2]["usage"]["completion_tokens"] == 3
    assert result[2]["usage"]["total_tokens"] == 6
    assert "throughput" in result[2]
