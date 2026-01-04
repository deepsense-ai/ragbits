"""
Ragbits Chat Example: Offline Chat Interface

This example demonstrates how to use the `ChatInterface` to create a simple chat application that works offline.
It showcases different response types, including text responses, live updates, and reference documents.

To run the script, execute the following command:

    ```bash
    ragbits api run examples.api.offline_chat:MyChat
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///

import asyncio
from collections.abc import AsyncGenerator
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.chat.persistence.file import FileHistoryPersistence
from ragbits.core.prompt import ChatFormat


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


class UserSettingsFormExample(BaseModel):
    """A simple example implementation of the chat form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(title="Chat Form", json_schema_serialization_defaults_required=True)

    language: Literal["English", "Polish"] = Field(description="Please select the language", default="English")


class MyChat(ChatInterface):
    """An offline example implementation of the ChatInterface that demonstrates different response types."""

    history_persistence = FileHistoryPersistence(base_path="chat_history")

    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )

    user_settings = UserSettings(form=UserSettingsFormExample)

    ui_customization = UICustomization(
        header=HeaderCustomization(title="Example Offline Ragbits Chat", subtitle="by deepsense.ai", logo="🐰"),
        welcome_message=(
            "Hello! I'm your AI assistant.\n\n How can I help you today?"
            "You can ask me *anything*! I can provide information, answer questions, and assist you with various tasks."
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
        history: ChatFormat,
        context: ChatContext,
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

        yield self.create_state_update({
            "example_state_key": "example_state_value",
            "example_state_key_2": "example_state_value_2",
        })

        example_live_updates = [
            self.create_live_update("0", LiveUpdateType.START, "[EXAMPLE] Searching for examples in the web..."),
            self.create_live_update(
                "0", LiveUpdateType.FINISH, "[EXAMPLE] Searched the web", "Found 11 matching results."
            ),
            self.create_live_update(
                "1",
                LiveUpdateType.FINISH,
                "[EXAMPLE] Ingested the results from previous query",
                "Found 4 connected topics.",
            ),
        ]

        for live_update in example_live_updates:
            yield live_update
            await asyncio.sleep(2)

        # Generate and yield text chunks
        async for chunk in self._generate_response(message):
            yield self.create_text_response(chunk)

        yield self.create_followup_messages(["Example Response 1", "Example Response 2", "Example Response 3"])
