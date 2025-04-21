# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///
from collections.abc import AsyncGenerator

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, FeedbackForm, FormField
from ragbits.chat.interface.types import ChatResponse, Message
from ragbits.core.llms import LiteLLM


class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface that demonstrates different response types."""

    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=FeedbackForm(
            title="Like Form",
            fields=[
                FormField(name="like_reason", type="text", required=True, label="Why do you like this?"),
            ],
        ),
        dislike_enabled=True,
        dislike_form=FeedbackForm(
            title="Dislike Form",
            fields=[
                FormField(
                    name="issue_type",
                    type="select",
                    required=True,
                    label="What was the issue?",
                    options=["Incorrect information", "Not helpful", "Unclear", "Other"],
                ),
                FormField(name="feedback", type="text", required=True, label="Please provide more details"),
            ],
        ),
    )

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: dict | None = None,
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
