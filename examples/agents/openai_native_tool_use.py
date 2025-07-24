"""
Ragbits Agents Example: OpenAI native tool use

This example shows how to use agent with native OpenAI tools.
We provide a single method as a tool to the agent and expect it to call it when answering query.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/openai_native_tool_use.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-agents[openai]",
# ]
# ///
import asyncio

from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.tools.openai import get_openai_tool
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class SearchPromptInput(BaseModel):
    """
    Input format for the Search Prompt.
    """

    query: str


class SearchPrompt(Prompt[SearchPromptInput]):
    """
    Prompt that does a web search with a given query.
    """

    system_prompt = """
    You are a helpful assistant that responds to user questions.
    """

    user_prompt = """
    Search web for {{ query }}.
    """


async def main() -> None:
    """
    Run the example.
    """
    model_name = "gpt-4o-2024-08-06"
    llm = LiteLLM(model_name=model_name, use_structured_output=True)
    agent = Agent(llm=llm, prompt=SearchPrompt, tools=[get_openai_tool({"type": "web_search_preview"}, model_name)])
    response = await agent.run(SearchPromptInput(query="What date is today?"))
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
