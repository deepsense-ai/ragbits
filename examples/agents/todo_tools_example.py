"""Example demonstrating the new orchestrator-based todo functionality with streaming."""

import asyncio

from ragbits.agents import Agent
from ragbits.agents.tools.todo import TodoOrchestrator
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.agents import ToolCallResult


async def hiking_guide():
    """Demonstrate the new orchestrator-based todo approach with streaming."""

    # Define the system prompt for hiking guide
    hiking_system_prompt = """
    You are an expert hiking guide. Provide detailed, comprehensive information
    about hiking routes, gear, transportation, and safety considerations.
    """

    # Create generic orchestrator with hiking domain context
    todo_orchestrator = TodoOrchestrator(
        domain_context="hiking guide"
    )

    # Create a simple agent - orchestrator handles the workflow
    agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt=hiking_system_prompt,
    )

    # Test queries
    # query = "Plan a 1-day hiking trip for 2 people in Tatra Mountains, Poland. Focus on scenic routes under 15km, avoiding crowds."
    query = "How long is hike to Giewont from Kuźnice?"

    print("=== Generic Todo Orchestrator - Hiking Example ===\n")

    # Run the complete workflow with orchestrator streaming
    async for response in todo_orchestrator.run_todo_workflow_streaming(agent, query):
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

            case dict():
                if response.get("type") == "status":
                    print(f"{response['message']}")
                elif response.get("type") == "task_list":
                    print(f"   {response['task_number']}. {response['task_description']}")
                elif response.get("type") == "task_summary_start":
                    print(f"{response['message']}", end="", flush=True)
                elif response.get("type") == "task_completed":
                    print(f"{response['message']}")
                elif response.get("type") == "final_summary_start":
                    print(f"{response['message']}", end="", flush=True)
                elif response.get("type") == "final_summary_end":
                    print(f"{response['message']}")

    print(f"\n🎯 Workflow completed successfully!")


async def software_architecture_example():
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

    todo_orchestrator = TodoOrchestrator(
        domain_context="software architect"
    )

    agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt=software_system_prompt,
    )

    query = "Design a scalable e-commerce platform for 100k+ users with real-time inventory management and payment processing."

    print("\n" + "="*60)
    print("=== Generic Todo Orchestrator - Software Architecture Example ===\n")

    async for response in todo_orchestrator.run_todo_workflow_streaming(agent, query):
        match response:
            case str():
                if response.strip():
                    print(response, end="", flush=True)
            case dict():
                if response.get("type") == "status":
                    print(f"{response['message']}")
                elif response.get("type") == "task_list":
                    print(f"   {response['task_number']}. {response['task_description']}")
                elif response.get("type") == "task_summary_start":
                    print(f"{response['message']}", end="", flush=True)
                elif response.get("type") == "task_completed":
                    print(f"{response['message']}")
                elif response.get("type") == "final_summary_start":
                    print(f"{response['message']}", end="", flush=True)
                elif response.get("type") == "final_summary_end":
                    print(f"{response['message']}")

    print(f"\n🎯 Software architecture workflow completed!")


async def demonstrate_both():
    """Demonstrate both hiking and software architecture examples."""
    await hiking_guide()
    # await software_architecture_example()


if __name__ == "__main__":
    asyncio.run(demonstrate_both())