"""
Example demonstrating an agent with tool confirmation using the new non-blocking approach.

This example shows how to create an agent that requires user confirmation
before executing certain tools. The confirmation is non-blocking: the agent
completes its run when a tool needs confirmation, and resumes after confirmation
is provided.

Run this example:
    uv run python examples/agents/agent_with_confirmation.py
"""

import asyncio

from ragbits.agents import Agent
from ragbits.agents._main import AgentRunContext
from ragbits.agents.confirmation import ConfirmationRequest
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
    """Run the agent with confirmation example using non-blocking approach."""
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

    print("\n" + "=" * 60)
    print("Agent with Non-Blocking Confirmation Example")
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

    # Store pending confirmations
    pending_confirmations: list[ConfirmationRequest] = []

    # First run - agent will encounter confirmation and stop
    agent_context: AgentRunContext = AgentRunContext()
    async for response in agent.run_streaming(user_query, context=agent_context):
        if isinstance(response, str):
            print(f"Agent: {response}", end="", flush=True)

        elif isinstance(response, ConfirmationRequest):
            pending_confirmations.append(response)
            print("\n\n⚠️  CONFIRMATION REQUIRED ⚠️")
            print(f"Tool: {response.tool_name}")
            print(f"Description: {response.tool_description}")
            print(f"Arguments: {response.arguments}")
            print(f"Confirmation ID: {response.confirmation_id}")

    # If we have pending confirmations, ask user and re-run agent
    if pending_confirmations:
        print("\n" + "-" * 60)
        user_input = input("\nDo you want to proceed with these actions? (yes/no): ").strip().lower()
        confirmed = user_input in ["yes", "y"]

        if confirmed:
            print("✅ Confirmed - re-running agent with confirmation\n")

            # Create new context with confirmations
            agent_context = AgentRunContext()
            # Pass confirmed tools to the agent context
            # This allows the agent to check if tools have been confirmed
            agent_context.confirmed_tools = [  # type: ignore[attr-defined]
                {"confirmation_id": req.confirmation_id, "confirmed": True} for req in pending_confirmations
            ]

            # Re-run agent with the same query and confirmations in context
            async for response in agent.run_streaming(user_query, context=agent_context):
                if isinstance(response, str):
                    print(f"Agent: {response}", end="", flush=True)
        else:
            print("❌ Cancelled - actions not performed")

    print("\n\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
