"""
Example demonstrating an agent with tool confirmation.

This example shows how to create an agent that requires user confirmation
before executing certain tools.

Run this example:
    uv run python examples/agents/agent_with_confirmation.py
"""

import asyncio
from types import SimpleNamespace

from ragbits.agents import Agent
from ragbits.agents._main import AgentDependencies, AgentRunContext
from ragbits.agents.confirmation import ConfirmationManager, ConfirmationRequest
from ragbits.core.llms import LiteLLM


# Define some example tools
def get_weather(city: str) -> str:
    """
    Get the weather for a city.

    Args:
        city: The city to get weather for
    """
    return f"☀️ Weather in {city}: Sunny, 72°F"


def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email to someone.

    Args:
        to: Email recipient
        subject: Email subject
        body: Email body
    """
    return f"📧 Email sent to {to} with subject '{subject}'"


def delete_file(filename: str) -> str:
    """
    Delete a file from the system.

    Args:
        filename: The file to delete
    """
    return f"🗑️ Deleted file: {filename}"


async def main() -> None:
    """Run the agent with confirmation example."""
    # Create LLM
    llm = LiteLLM(model_name="gpt-4o-mini")

    # Create agent
    agent: Agent = Agent(
        llm=llm,
        prompt="You are a helpful assistant. Help the user with their requests.",
        tools=[get_weather, send_email, delete_file],
    )

    # Mark tools that require confirmation
    for tool in agent.tools:
        if tool.name in ["send_email", "delete_file"]:
            tool.requires_confirmation = True
            print(f"✓ Tool '{tool.name}' marked as requiring confirmation")

    # Create confirmation manager
    confirmation_manager = ConfirmationManager()

    # Create agent context with confirmation manager
    deps_value = SimpleNamespace(confirmation_manager=confirmation_manager)
    agent_context = AgentRunContext(deps=AgentDependencies(value=deps_value))

    print("\n" + "=" * 60)
    print("Agent with Confirmation Example")
    print("=" * 60)
    print("\nTools available:")
    print("  - get_weather (no confirmation)")
    print("  - send_email (requires confirmation)")
    print("  - delete_file (requires confirmation)")
    print("\nTry: 'Send an email to john@example.com about the meeting'")
    print("=" * 60 + "\n")

    # Test query
    user_query = "Send an email to john@example.com with subject 'Meeting Reminder' about our 2pm meeting tomorrow"

    print(f"User: {user_query}\n")

    # Stream agent responses
    async for response in agent.run_streaming(user_query, context=agent_context):
        if isinstance(response, str):
            print(f"Agent: {response}", end="", flush=True)

        elif isinstance(response, ConfirmationRequest):
            print("\n\n⚠️  CONFIRMATION REQUIRED ⚠️")
            print(f"Tool: {response.tool_name}")
            print(f"Description: {response.tool_description}")
            print(f"Arguments: {response.arguments}")
            print(f"Timeout: {response.timeout_seconds}s")

            # Simulate user input
            user_input = input("\nDo you want to proceed? (yes/no): ").strip().lower()

            confirmed = user_input in ["yes", "y"]
            confirmation_manager.resolve_confirmation(response.confirmation_id, confirmed)

            if confirmed:
                print("✅ Confirmed - proceeding with action\n")
            else:
                print("❌ Cancelled - skipping action\n")

    print("\n\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
