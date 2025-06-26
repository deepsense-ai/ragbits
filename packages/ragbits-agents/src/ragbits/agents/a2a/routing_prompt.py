from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class RoutingPromptInput(BaseModel):
    """Input model for RoutingPrompt."""

    message: str
    agents: list


class RoutingPrompt(Prompt[RoutingPromptInput]):
    """
    Prompt template for routing a user message to appropriate agents.

    System prompt instructs the agent to output a JSON list of tasks,
    each containing agent URL, tool name, and parameters to call.
    """

    system_prompt = """
    You are a router agent. Your task is to read the user's message and output a list of tasks in JSON format.

    Each task must include:
    - agent_url: The base URL of the agent that should handle the task.
    - tool: The name of the skill/tool to call on that agent.
    - parameters: A dictionary of arguments needed for that tool.

    Currently available agents and their tools:
    {{ agents }}

    Return your output as a **JSON list** of tasks. Your response must be only the JSON list (e.g. starting with `[`).

    If there are multiple tasks in the user request, return multiple entries in the list.

    Example:
    User: "Check weather in Paris and get a summary of recent news from France"

    Output:
    [
    {
        "agent_url": "http://weather-agent:8000",
        "tool": "get_weather",
        "parameters": { "location": "Paris" }
    },
    {
        "agent_url": "http://news-agent:8001",
        "tool": "get_news_summary",
        "parameters": { "region": "France" }
    }
    ]
    """
    user_prompt = "{{ message }}"
