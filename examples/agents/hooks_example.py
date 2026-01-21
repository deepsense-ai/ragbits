"""
Example demonstrating custom hooks for tool lifecycle management.

This example shows:
1. Access control hook (deny specific tools)
2. Input validation hook (modify tool arguments)
3. Output filtering hook (modify tool results)
4. Hook priority system
"""

import asyncio
from typing import Any

from ragbits.agents import Agent, EventType, Hook, PreToolInput, PreToolOutput, PostToolInput, PostToolOutput
from ragbits.core.llms.litellm import LiteLLM


# ============================================================================
# Pre-Tool Hooks
# ============================================================================

async def access_control_hook(input_data: PreToolInput) -> PreToolOutput | None:
    """Block access to sensitive tools."""
    blocked_tools = ["delete_file", "system_command"]

    if input_data.tool_name in blocked_tools:
        return PreToolOutput(
            action="deny",
            result=f"Access denied: '{input_data.tool_name}' is blocked by security policy"
        )
    return None


async def input_sanitizer_hook(input_data: PreToolInput) -> PreToolOutput | None:
    """Sanitize and validate tool inputs."""
    if input_data.tool_name == "search":
        # Ensure query is not empty
        query = input_data.tool_input.get("query", "")
        if not query.strip():
            return PreToolOutput(
                action="modify",
                result={"query": "default search"}
            )
    return None


# ============================================================================
# Post-Tool Hooks
# ============================================================================

async def output_filter_hook(input_data: PostToolInput) -> PostToolOutput | None:
    """Filter sensitive information from tool outputs."""
    if input_data.tool_name == "get_user_data":
        if input_data.tool_output and isinstance(input_data.tool_output, dict):
            # Remove sensitive fields
            filtered_output = {k: v for k, v in input_data.tool_output.items() if k != "password"}
            return PostToolOutput(
                action="modify",
                result=filtered_output
            )
    return None


async def error_handler_hook(input_data: PostToolInput) -> PostToolOutput | None:
    """Provide friendly error messages."""
    if input_data.error:
        return PostToolOutput(
            action="modify",
            result=f"Tool '{input_data.tool_name}' failed: {str(input_data.error)[:100]}"
        )
    return None


# ============================================================================
# Example Tools
# ============================================================================

def search(query: str) -> str:
    """Search for information."""
    return f"Search results for: {query}"


def get_user_data(user_id: str) -> dict[str, Any]:
    """Get user data (contains sensitive info)."""
    return {"id": user_id, "name": "John Doe", "password": "secret123"}


def delete_file(path: str) -> str:
    """Delete a file (blocked by security)."""
    return f"Deleted {path}"


# ============================================================================
# Main Example
# ============================================================================

async def main():
    """Run the hooks example."""
    ...
    # Create hooks with different priorities
    hooks = [
        Hook(
            event_type=EventType.PRE_TOOL,
            callback=access_control_hook,
            priority=10  # High priority - runs first
        ),
        Hook(
            event_type=EventType.PRE_TOOL,
            callback=input_sanitizer_hook,
            priority=20  # Lower priority - runs second
        ),
        Hook(
            event_type=EventType.POST_TOOL,
            callback=output_filter_hook,
            priority=10
        ),
        Hook(
            event_type=EventType.POST_TOOL,
            callback=error_handler_hook,
            priority=5  # Runs before output_filter
        ),
    ]

    # Create agent with hooks
    llm = LiteLLM("gpt-4o-mini")
    agent = Agent(
        llm=llm,
        tools=[search, get_user_data, delete_file],
        hooks=hooks
    )

    # Test cases
    test_queries = [
        "Search for Python tutorials",
        "Get user data for user123",
        "Delete the temp file",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        try:
            result = await agent.run(query)
            print(f"Result: {result.response}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
