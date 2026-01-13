"""Example demonstrating the new orchestrator-based todo functionality with streaming."""

import asyncio
from types import SimpleNamespace

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents._main import DownstreamAgentResult
from ragbits.agents.tools.todo import ToDoPlanner, TodoResult
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.llms.base import Usage
from ragbits.core.prompt.base import BasePrompt

# Type alias for response types
ResponseType = (
    str | ToolCall | ToolCallResult | TodoResult | BasePrompt | Usage | SimpleNamespace | DownstreamAgentResult
)


def _handle_response(response: ResponseType) -> None:
    """Handle different types of responses from the orchestrator."""
    match response:
        case str():
            if response.strip():
                print(response, end="", flush=True)
        case ToolCall():
            print(f"\n🔧 Tool Call: {response.name}")
            if response.arguments:
                print(f"   Arguments: {response.arguments}")
        case ToolCallResult():
            print(f"🔧 Tool Result: {response.result}")
        case TodoResult():
            _handle_streaming_response(response)


def _handle_streaming_response(response: TodoResult) -> None:
    """Handle TodoResult from the orchestrator."""
    if response.type in ("status"):
        print(response.message or "")
    elif response.type in ("task_list"):
        for index, task in enumerate(response.tasks, 1):
            print(f"{index}. {task.description}")
    elif response.type in ("task_summary_start", "final_summary_start"):
        print(response.message or "", end="", flush=True)
    elif response.type in ("task_completed", "final_summary_end"):
        print(response.message or "")


async def hiking_guide() -> None:
    """Demonstrate the new orchestrator-based todo approach with streaming."""
    # Define the system prompt for hiking guide
    hiking_system_prompt = """
    You are an expert hiking guide. Provide detailed, comprehensive information
    about hiking routes, gear, transportation, and safety considerations.
    """

    # Create generic orchestrator with hiking domain context
    todo_orchestrator = ToDoPlanner(domain_context="hiking guide")

    # Create a simple agent - orchestrator handles the workflow
    agent: Agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt=hiking_system_prompt,
    )

    # Test queries
    query = (
        "Plan a 1-day hiking trip for 2 people in Tatra Mountains, Poland. "
        "Focus on scenic routes under 15km, avoiding crowds."
    )
    # query = "How long is hike to Giewont from Kuźnice?"

    print("=== Generic Todo Orchestrator - Hiking Example ===\n")

    # Run the complete workflow with orchestrator streaming
    async for response in todo_orchestrator.run_todo_workflow_streaming(agent, query):
        _handle_response(response)

    print("\n🎯 Workflow completed successfully!")


async def software_architecture_example() -> None:
    """Example showing the orchestrator used for software architecture."""
    software_system_prompt = """
    You are an expert software architect. Provide detailed technical analysis,
    system design recommendations, and implementation guidance.

    Always be specific with:
    - Technology stack recommendations with versions
    - Architecture patterns and design principles
    - Performance and scalability considerations
    - Security best practices
    - Implementation roadmap with timelines
    """

    todo_orchestrator = ToDoPlanner(domain_context="software architect")

    agent: Agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt=software_system_prompt,
    )

    query = (
        "Design a scalable e-commerce platform for 100k+ users with "
        "real-time inventory management and payment processing."
    )

    print("\n" + "=" * 60)
    print("=== Generic Todo Orchestrator - Software Architecture Example ===\n")

    async for response in todo_orchestrator.run_todo_workflow_streaming(agent, query):
        _handle_response(response)

    print("\n🎯 Software architecture workflow completed!")


async def demonstrate_both() -> None:
    """Demonstrate both hiking and software architecture examples."""
    await hiking_guide()
    # await software_architecture_example()


if __name__ == "__main__":
    asyncio.run(demonstrate_both())
