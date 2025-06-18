# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///
#
# To run this example execute following CLI command:
# ragbits api run examples.api.chat:MyChat

from collections.abc import AsyncGenerator
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig
from ragbits.chat.interface.types import ChatContext, ChatResponse, Message
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM


class LikeFormExample(BaseModel):
    """A simple example implementation of the like form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(
        title="Like Form",
        json_schema_serialization_defaults_required=True,
    )

    like_reason: str = Field(
        description="Why do you like this?",
        min_length=1,
    )


class DislikeFormExample(BaseModel):
    """A simple example implementation of the dislike form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(title="Dislike Form", json_schema_serialization_defaults_required=True)

    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(
        description="What was the issue?"
    )
    feedback: str = Field(description="Please provide more details", min_length=1)


class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface that demonstrates different response types."""

    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )

    ui_customization = UICustomization(
        header=HeaderCustomization(title="Example Ragbits Chat", subtitle="by deepsense.ai", logo="🐰"),
        welcome_message=(
            "Hello! I'm your AI assistant.\n\n How can I help you today? "
            "You can ask me **anything**! "
            "I can provide information, answer questions, and assist you with various tasks."
        ),
    )

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Example implementation of the ChatInterface.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - Reference documents used to generate the response
        """
        yield self.create_reference(
            title="Example Reference",
            content="This is an example reference document that might be relevant to your query.",
            url="https://example.com/reference1",
        )

        async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
            yield self.create_text_response(chunk)
