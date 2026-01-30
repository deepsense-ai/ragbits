"""
Example demonstrating hooks for input validation, sanitization, and output masking.

This example shows a customer support agent with hooks that:
- Validate email addresses before sending
- Sanitize email domains to approved list
- Mask sensitive user data in responses
"""

import asyncio
import re
from typing import Any

from ragbits.agents import Agent
from ragbits.agents.hooks import EventType, Hook, PostToolInput, PostToolOutput, PreToolInput, PreToolOutput
from ragbits.core.llms.litellm import LiteLLM

# Track hook actions for demonstration
hook_actions: list[dict[str, Any]] = []


def search_user(user_id: str) -> dict[str, Any]:
    """Search for user information in the database."""
    users = {
        "123": {"name": "John Doe", "email": "john@example.com", "ssn": "123-45-6789", "balance": 5000},
        "456": {"name": "Jane Smith", "email": "jane@example.com", "ssn": "987-65-4321", "balance": 3500},
    }
    return users.get(user_id, {"error": "User not found"})


def send_notification(email: str, message: str) -> str:
    """Send notification email to user."""
    return f"Email sent to {email}: {message}"


async def validate_email(input_data: PreToolInput) -> PreToolOutput:
    """Validate email format before sending."""
    if input_data.tool_call.name != "send_notification":
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    email = input_data.tool_call.arguments.get("email", "")
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_pattern, email):
        hook_actions.append({"hook": "validate_email", "action": "denied", "email": email})
        return PreToolOutput(
            arguments=input_data.tool_call.arguments,
            decision="deny",
            reason=f"Invalid email format: {email}",
        )

    hook_actions.append({"hook": "validate_email", "action": "passed", "email": email})
    return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")


async def sanitize_email_domain(input_data: PreToolInput) -> PreToolOutput:
    """Ensure emails only go to approved domains."""
    if input_data.tool_call.name != "send_notification":
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    email = input_data.tool_call.arguments.get("email", "")
    approved_domains = ["example.com", "test.com"]

    domain = email.split("@")[-1] if "@" in email else ""
    if domain not in approved_domains:
        modified_email = email.split("@")[0] + "@example.com"
        modified_args = input_data.tool_call.arguments.copy()
        modified_args["email"] = modified_email

        hook_actions.append(
            {
                "hook": "sanitize_email_domain",
                "action": "modified",
                "original": email,
                "modified": modified_email,
            }
        )

        return PreToolOutput(
            arguments=modified_args,
            decision="pass",
            reason=f"Redirected {email} to approved domain: {modified_email}",
        )

    hook_actions.append({"hook": "sanitize_email_domain", "action": "passed", "email": email})
    return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")


async def mask_sensitive_data(input_data: PostToolInput) -> PostToolOutput:
    """Mask sensitive information in user search results."""
    if input_data.tool_call.name != "search_user":
        return PostToolOutput(output=input_data.output)

    if isinstance(input_data.output, dict) and "ssn" in input_data.output:
        original_ssn = input_data.output["ssn"]
        masked_output = input_data.output.copy()
        masked_output["ssn"] = "***-**-****"

        hook_actions.append(
            {
                "hook": "mask_sensitive_data",
                "action": "masked",
                "field": "ssn",
                "original": original_ssn,
                "masked": "***-**-****",
            }
        )

        return PostToolOutput(output=masked_output)

    return PostToolOutput(output=input_data.output)


async def log_notification(input_data: PostToolInput) -> PostToolOutput:
    """Add logging metadata to notification results."""
    if input_data.tool_call.name != "send_notification":
        return PostToolOutput(output=input_data.output)

    original_output = input_data.output
    enhanced_output = f"{input_data.output} [Logged at system]"

    hook_actions.append(
        {
            "hook": "log_notification",
            "action": "enhanced",
            "original": original_output,
            "enhanced": enhanced_output,
        }
    )

    return PostToolOutput(output=enhanced_output)


async def main() -> None:
    """Run the hooks example demonstrating pre-tool and post-tool hooks."""
    llm = LiteLLM("gpt-4o-mini")

    hooks = [
        Hook(event_type=EventType.PRE_TOOL, callback=validate_email, tool_names=["send_notification"], priority=10),
        Hook(
            event_type=EventType.PRE_TOOL, callback=sanitize_email_domain, tool_names=["send_notification"], priority=20
        ),
        Hook(event_type=EventType.POST_TOOL, callback=mask_sensitive_data, tool_names=["search_user"], priority=10),
        Hook(event_type=EventType.POST_TOOL, callback=log_notification, tool_names=["send_notification"], priority=10),
    ]

    agent = Agent(
        llm=llm,
        tools=[search_user, send_notification],
        hooks=hooks,
    )

    prompt = "Look up user 123 and send them a notification about their account balance."

    print(f"Prompt: {prompt}\n")

    response = await agent.run(prompt)

    print(f"\nAgent Response: {response.content}\n")

    print("Tool Results:")
    for tool_call in response.tool_calls:
        if tool_call.name == "search_user":
            result = tool_call.result
            print(f"  search_user: name={result['name']}, ssn={result['ssn']}, balance=${result['balance']}")
        elif tool_call.name == "send_notification":
            print(f"  send_notification: {tool_call.result}")

    print("\nHook Actions:")
    for action in hook_actions:
        if action["hook"] == "mask_sensitive_data":
            print(f"  {action['field'].upper()} masked: {action['original']} → {action['masked']}")
        elif action["hook"] == "validate_email":
            print(f"  Email validation {action['action']}: {action['email']}")
        elif action["hook"] == "sanitize_email_domain":
            if action["action"] == "modified":
                print(f"  Domain redirected: {action['original']} → {action['modified']}")
            else:
                print(f"  Domain approved: {action['email']}")
        elif action["hook"] == "log_notification":
            print("  Output enhanced with logging metadata")


if __name__ == "__main__":
    asyncio.run(main())
