import base64
from collections.abc import Callable

from openai import AsyncOpenAI
from openai.types.responses import Response
from openai.types.responses.tool_param import ToolParam


class OpenAIResponsesLLM:
    """
    Class serving as a wrapper for tool calls to responses API of OpenAI
    """

    def __init__(self, model_name: str, tool_param: ToolParam):
        self._client = AsyncOpenAI()
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

    def __init__(self, model_name: str, tool_param: ToolParam):
        self._responses_llm = OpenAIResponsesLLM(model_name, tool_param)

    async def search_web(self, query: str) -> str:
        """
        Searches web for a query

        Args:
            query: The query to search

        Returns:
            The web search result
        """
        return (await self._responses_llm.use_tool(query)).output_text

    async def code_interpreter(self, query: str) -> str:
        """
        Performs actions in code interpreter based on query

        Args:
            query: The query with instructions

        Returns:
            Output of the interpreter
        """
        return (await self._responses_llm.use_tool(query)).output_text

    async def image_generation(self, query: str, save_path: str = "generated_image.png") -> str:
        """
        Generate image based on query.

        Args:
            query: The query with instructions
            save_path: The path to save the generated image

        Returns:
            LLM text output
        """
        response = await self._responses_llm.use_tool(query)
        image_data = next((output.result for output in response.output if output.type == "image_generation_call"), None)

        if image_data:
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            text_prefix = f"Image saved to {save_path}\n"
        else:
            text_prefix = "No generated image was returned\n"

        return text_prefix + response.output_text


def get_openai_tool(tool_param: ToolParam, model_name: str) -> Callable:
    """
    Returns a native OpenAI tool as function

    Args:
        tool_param: The tool parameters
        model_name: The name of the model

    Returns:
        Function using OpenAI tool
    """
    tool_type = tool_param.get("type")
    match tool_type:
        case "web_search_preview":
            return OpenAITools(model_name, tool_param).search_web
        case "code_interpreter":
            return OpenAITools(model_name, tool_param).code_interpreter
        case "image_generation":
            return OpenAITools(model_name, tool_param).image_generation
    raise ValueError(f"{tool_type} is not a valid tool type. You can use one of {OpenAITools.AVAILABLE_TOOLS}")
