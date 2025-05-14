# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///
#
# To run this example execute following CLI command:
# ragbits api run examples.api.offline_chat:MyChat

import asyncio
from collections.abc import AsyncGenerator

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, FeedbackForm, FormField
from ragbits.chat.interface.types import ChatResponse, Message
from ragbits.chat.persistence.file import FileHistoryPersistence


class MyChat(ChatInterface):
    """An offline example implementation of the ChatInterface that demonstrates different response types."""

    history_persistence = FileHistoryPersistence(file_path="offline_chat_history.json")

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

    @staticmethod
    async def _generate_response(message: str) -> AsyncGenerator[str, None]:
        """Simple response generator that simulates streaming text."""
        # Simple echo response with some additional text
        response = f"I received your message: '{message}'. This is an offline response."

        # Simulate streaming by yielding character by character
        for char in response:
            yield char
            await asyncio.sleep(0.05)  # Add small delay to simulate streaming

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: dict | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Offline implementation of the ChatInterface.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - Reference documents used to generate the response
        """
        # Example of yielding a reference
        yield self.create_reference(
            title="Offline Reference",
            content="This is an example reference document that might be relevant to your query.",
            url="https://example.com/offline-reference",
        )

        # Generate and yield text chunks
        async for chunk in self._generate_response(message):
            yield self.create_text_response(chunk)
