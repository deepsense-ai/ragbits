"""
Ragbits Chat Example: Chat with Attachments

This example demonstrates how a `ChatInterface` can receive files attached to a
chat message and forward them to the LLM for analysis. Files arrive in
`ChatContext.attachments` (populated by the server from multipart parts of the
`/api/chat` request) and are passed through to a Prompt as `Attachment` fields.

To run the script, execute the following command:

    ```bash
    ragbits api run examples.chat.attachment_chat:AttachmentChat
    ```

Then open the UI and use the attachment icon in the input bar to attach an
image or PDF before sending a message.
"""
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///

from collections import defaultdict
from collections.abc import AsyncGenerator

from pydantic import BaseModel

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Attachment, ChatFormat, Prompt


class AttachmentPromptInput(BaseModel):
    """Input for the attachment-analysis prompt."""

    question: str
    files: list[Attachment] = []


class AttachmentPrompt(Prompt[AttachmentPromptInput, str]):
    """Asks the LLM to analyze any attached files in light of the user question."""

    system_prompt = """
    You are a helpful assistant analyzing files attached by the user.
    If files are attached, describe what you see in them as you answer.
    """

    user_prompt = "{{ question }}"


class AttachmentChat(ChatInterface):
    """A ChatInterface that forwards attached files to the LLM for analysis."""

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="Attachment Chat Example",
            subtitle="Attach an image or PDF and ask about it",
            logo="📎",
        ),
        welcome_message=("Hi! Click the attachment icon, drop in an image or PDF, " "and ask me a question about it."),
    )

    supports_upload = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")
        self.history = defaultdict(list)  # keeping history on the backend (use an actual database in production)

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Implementation of the main chat method supporting attachments and storing the content within the conversation
        history.
        """
        prompt = AttachmentPrompt(
            AttachmentPromptInput(question=message, files=context.attachments),
            history=self.history[context.conversation_id],
        )
        response = self.llm.generate_streaming(prompt)
        async for chunk in response:
            yield self.create_text_response(chunk)
        self.history[context.conversation_id] = prompt.chat + [{"role": "assistant", "content": response.content}]


if __name__ == "__main__":
    from ragbits.chat.api import RagbitsAPI

    RagbitsAPI(AttachmentChat).run()
