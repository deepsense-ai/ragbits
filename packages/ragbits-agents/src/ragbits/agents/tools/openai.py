import base64
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import cast

from openai import AsyncOpenAI
from openai.types.responses import Response
from openai.types.responses.tool_param import CodeInterpreter, ToolParam

from ragbits.agents.tools.types import ImageGenerationResponse
from ragbits.core.sources.base import get_local_storage_dir


def get_web_search_tool(model_name: str, api_key: str | None = None, additional_params: dict | None = None) -> Callable:
    """
    Returns a native OpenAI web search tool as function

    Args:
        model_name: The name of the model
        api_key: The API key for the model
        additional_params: The additional tool parameters

    Returns:
        web search function
    """
    params_to_pass = additional_params if additional_params else {}
    tool_object = OpenAITools(model_name, api_key, {"type": "web_search_preview", **params_to_pass})
    return tool_object.search_web


def get_code_interpreter_tool(
    model_name: str, api_key: str | None = None, additional_params: dict | None = None
) -> Callable:
    """
    Returns a native OpenAI code interpreter tool as function

    Args:
        model_name: The name of the model
        api_key: The API key for the model
        additional_params: The additional tool parameters

    Returns:
        code interpreter function
    """
    params_to_pass = additional_params if additional_params else {}
    tool_object = OpenAITools(
        model_name, api_key, cast(CodeInterpreter, {"type": "code_interpreter", **params_to_pass})
    )
    return tool_object.code_interpreter


def get_image_generation_tool(
    model_name: str, api_key: str | None = None, additional_params: dict | None = None
) -> Callable:
    """
    Returns a native OpenAI image generation tool as function

    Args:
        model_name: The name of the model
        api_key: The API key for the model
        additional_params: The additional tool parameters

    Returns:
        image generation function
    """
    params_to_pass = additional_params if additional_params else {}
    tool_object = OpenAITools(model_name, api_key, {"type": "image_generation", **params_to_pass})
    return tool_object.image_generation


class OpenAIResponsesLLM:
    """
    Class serving as a wrapper for tool calls to responses API of OpenAI
    """

    def __init__(self, model_name: str, api_key: str | None, tool_param: ToolParam):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name
        self._tool_param = tool_param

    async def use_tool(self, query: str) -> Response:
        """
        Uses tool based on query and returns output.

        Args:
            query: query for the tool

        Returns:
            Output of the tool
        """
        return await self._client.responses.create(
            model=self._model_name,
            tools=[self._tool_param],
            tool_choice="required",
            input=query,
        )


class OpenAITools:
    """
    Class wrapping tool calls to responses API of OpenAI
    """

    AVAILABLE_TOOLS = {"web_search_preview", "code_interpreter", "image_generation"}

    def __init__(self, model_name: str, api_key: str | None, tool_param: ToolParam):
        self._responses_llm = OpenAIResponsesLLM(model_name, api_key, tool_param)

    async def search_web(self, query: str) -> Response:
        """
        Searches web for a query

        Args:
            query: The query to search

        Returns:
            The web search result
        """
        return await self._responses_llm.use_tool(query)

    async def code_interpreter(self, query: str) -> Response:
        """
        Performs actions in code interpreter based on query

        Args:
            query: The query with instructions

        Returns:
            Output of the interpreter
        """
        return await self._responses_llm.use_tool(query)

    async def image_generation(self, query: str, save_path: str | Path | None = None) -> ImageGenerationResponse:
        """
        Generate image based on query.

        Args:
            query: The query with instructions
            save_path: The path to save the generated image

        Returns:
            LLM dict with image_path and output_text
        """
        if save_path is None:
            save_path = get_local_storage_dir() / f"{uuid.uuid4()}.png"

        response = await self._responses_llm.use_tool(query)
        image_data = next((output.result for output in response.output if output.type == "image_generation_call"), None)

        if image_data:
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            return ImageGenerationResponse(image_path=save_path, output_text=response.output_text)
        else:
            return ImageGenerationResponse(image_path=None, output_text=response.output_text)
