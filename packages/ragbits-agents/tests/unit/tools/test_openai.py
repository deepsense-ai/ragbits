import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.agents.tools.openai import OpenAITools, get_openai_tool


@pytest.fixture
def mock_responses_llm() -> MagicMock:
    """Fixture for mocking OpenAIResponsesLLM."""
    mock = MagicMock()
    mock.use_tool = AsyncMock()
    return mock


@pytest.mark.parametrize(
    ("tool_name", "should_succeed"),
    [
        ("search_web", True),
        ("code_interpreter", True),
        ("image_generation", True),
        ("non_existing_tool", False),
    ],
)
def test_get_openai_tool(tool_name: str, should_succeed: bool) -> None:
    """Test that get_openai_tool returns the correct tool."""
    if should_succeed:
        tool = get_openai_tool(tool_name, "test_model")
        assert callable(tool)
    else:
        with pytest.raises(ValueError):
            get_openai_tool(tool_name, "test_model")


async def test_search_web(mock_responses_llm: MagicMock) -> None:
    """Test that search_web calls use_tool and returns output_text."""
    mock_response = MagicMock()
    mock_response.output_text = "Test output"
    mock_responses_llm.use_tool.return_value = mock_response
    tools = OpenAITools("test_model", tool_param=MagicMock())
    tools._responses_llm = mock_responses_llm

    result = await tools.search_web("test query")

    mock_responses_llm.use_tool.assert_called_once_with("test query")
    assert result == "Test output"


async def test_code_interpreter(mock_responses_llm: MagicMock) -> None:
    """Test that code_interpreter calls use_tool and returns output_text."""
    mock_response = MagicMock()
    mock_response.output_text = "Interpreter output"
    mock_responses_llm.use_tool.return_value = mock_response
    tools = OpenAITools("test_model", tool_param=MagicMock())
    tools._responses_llm = mock_responses_llm

    result = await tools.code_interpreter("run code")

    mock_responses_llm.use_tool.assert_called_once_with("run code")
    assert result == "Interpreter output"


@patch("builtins.open", new_callable=MagicMock)
async def test_image_generation(mock_open: MagicMock, mock_responses_llm: MagicMock) -> None:
    """Test image_generation saves image and returns correct text."""
    image_data = base64.b64encode(b"test_image_content").decode("utf-8")

    mock_output_item = MagicMock()
    mock_output_item.type = "image_generation_call"
    mock_output_item.result = image_data

    mock_response = MagicMock()
    mock_response.output_text = "Generated image."
    mock_response.output = [mock_output_item]

    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle

    mock_responses_llm.use_tool.return_value = mock_response
    tools = OpenAITools("test_model", tool_param=MagicMock())
    tools._responses_llm = mock_responses_llm

    result = await tools.image_generation("a cat", save_path="cat.png")

    mock_responses_llm.use_tool.assert_called_once_with("a cat")
    mock_open.assert_called_once_with("cat.png", "wb")
    mock_file_handle.write.assert_called_once_with(b"test_image_content")
    assert result == "Image saved to cat.png\nGenerated image."


async def test_image_generation_no_image(mock_responses_llm: MagicMock) -> None:
    """Test image_generation when no image is returned."""
    mock_output_item = MagicMock()
    mock_output_item.type = "image_generation_call"
    mock_output_item.result = None

    mock_response = MagicMock()
    mock_response.output_text = "No image was generated."
    mock_response.output = [mock_output_item]

    mock_responses_llm.use_tool.return_value = mock_response
    tools = OpenAITools("test_model", tool_param=MagicMock())
    tools._responses_llm = mock_responses_llm

    result = await tools.image_generation("a dog")

    assert result == "No generated image was returned\nNo image was generated."
