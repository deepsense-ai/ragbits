"""
Simple example of custom response types in Ragbits Chat.

This is a minimal example showing how to create and use custom response types.
Perfect for getting started!

Run with:
    ragbits api run simple_custom_response:SimpleCustomChat
"""

from collections.abc import AsyncGenerator
from typing import Literal

from pydantic import Field

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, ResponseContent
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import ChatFormat


# ============================================================================
# Example 1: User Profile
# ============================================================================
class UserProfileContent(ResponseContent):
    """Simple user profile information.

    This demonstrates the basic structure of a custom response content type.
    """

    name: str = Field(..., min_length=1, description="User's full name")
    age: int = Field(..., ge=0, le=150, description="User's age")
    email: str = Field(..., description="User's email address")
    bio: str | None = Field(default=None, description="Optional biography")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content.

        This identifier is used by the frontend to determine how to render the response.
        """
        return "user_profile"


class UserProfileResponse(ChatResponse[UserProfileContent]):
    """User profile response for streaming to clients.

    This is a simple wrapper around UserProfileContent that makes it
    compatible with the Ragbits chat streaming API.
    """


# ============================================================================
# Example 2: Chart Data
# ============================================================================
class ChartDataContent(ResponseContent):
    """Chart visualization data.

    This shows how to send structured data for visualizations.
    """

    title: str = Field(..., description="Chart title")
    labels: list[str] = Field(..., description="X-axis labels")
    values: list[float] = Field(..., description="Y-axis values")
    chart_type: Literal["line", "bar", "pie", "scatter"] = Field(default="line", description="Type of chart")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content."""
        return "chart_data"


class ChartDataResponse(ChatResponse[ChartDataContent]):
    """Chart data response for streaming to clients."""


# ============================================================================
# Chat Implementation
# ============================================================================
class SimpleCustomChat(ChatInterface):
    """Simple chat demonstrating custom response types.

    Try asking:
    - "show me a user profile"
    - "show me a chart"
    - Any other question for normal LLM conversation
    """

    def __init__(self) -> None:
        """Initialize the chat with an LLM."""
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle incoming chat messages."""
        message_lower = message.lower()

        # Example 1: User Profile
        if "profile" in message_lower:
            yield self.create_text_response("Here's an example user profile:")

            # Create the custom content
            profile = UserProfileContent(
                name="Alice Johnson",
                age=28,
                email="alice@example.com",
                bio="Software engineer passionate about AI and machine learning",
            )

            # Yield the custom response
            yield UserProfileResponse(content=profile)

            yield self.create_text_response("\n✅ This is a custom response type with full type safety!")

        # Example 2: Chart Data
        elif "chart" in message_lower or "graph" in message_lower:
            yield self.create_text_response("Here's some example chart data:")

            # Create the custom content
            chart = ChartDataContent(
                title="Quarterly Revenue",
                labels=["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"],
                values=[125.5, 150.2, 143.8, 180.3],
                chart_type="bar",
            )

            # Yield the custom response
            yield ChartDataResponse(content=chart)

            yield self.create_text_response(
                "\n✅ This data is fully typed and validated with Pydantic!\n"
                "\nThe frontend can use the 'chart_data' type to render this as a chart."
            )

        # Default: Normal LLM conversation
        else:
            yield self.create_text_response("💡 Try asking:\n" "- 'show me a user profile'\n" "- 'show me a chart'\n\n")

            # Generate a normal response using the LLM
            async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
                yield self.create_text_response(chunk)


if __name__ == "__main__":
    print("Simple Custom Response Example")
    print("=" * 50)
    print()
    print("This is a minimal example of custom response types in Ragbits.")
    print()
    print("To run:")
    print("  ragbits api run simple_custom_response:SimpleCustomChat")
    print()
    print("Then open: http://127.0.0.1:8000")
    print()
    print("Try these commands:")
    print("  - 'show me a user profile'")
    print("  - 'show me a chart'")
    print()
