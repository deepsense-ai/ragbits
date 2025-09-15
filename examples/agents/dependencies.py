from dataclasses import dataclass

from ragbits.agents import Agent, AgentRunContext
from ragbits.core.llms.mock import MockLLM, MockLLMOptions


@dataclass
class Deps:
    """Simple dependency container used by the agent tools."""

    api_host: str


def get_api_host(context: AgentRunContext | None) -> str:
    """Return the API host taken from the bound dependencies in context."""
    if context is None:
        raise ValueError("Missing AgentRunContext")
    return context.deps.api_host


async def main() -> None:
    """Bind dependencies, run the agent, and access them inside a tool."""
    llm = MockLLM(
        default_options=MockLLMOptions(
            response="Using dependencies from context.",
            tool_calls=[
                {
                    "name": "get_api_host",
                    "arguments": "{}",
                    "id": "example",
                    "type": "function",
                }
            ],
        )
    )

    agent = Agent(llm=llm, prompt="Retrieve API host", tools=[get_api_host])

    context = AgentRunContext()
    context.deps.value = Deps(api_host="https://api.local")

    result = await agent.run("What host are we using?", context=context)
    print(result.tool_calls[0].result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
