"""
Ragbits Chat Example: File Upload Chat

This example demonstrates how to use the `ChatInterface` with file upload capability.
It shows how to implement the `upload_handler` to process uploaded files.

To run the script, execute the following command:

    ```bash
    ragbits api run examples.chat.upload_chat:UploadChat
    ```
"""

from collections.abc import AsyncGenerator

from fastapi import UploadFile

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.prompt import ChatFormat


class UploadChat(ChatInterface):
    """An example ChatInterface that supports file uploads."""

    ui_customization = UICustomization(
        header=HeaderCustomization(title="Upload Chat Example", subtitle="Demonstrating file uploads", logo="📁"),
        welcome_message=(
            "Hello! I am a chat bot that can handle file uploads.\n\n"
            "Click the attachment icon in the input bar to upload a file. "
            "I will tell you the size and name of the file you uploaded."
        ),
    )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Simple echo chat that responds to text.
        """
        yield self.create_text_response(f"You said: {message}")

    async def upload_handler(self, file: UploadFile) -> None:  # noqa: PLR6301
        """
        Handle file uploads.

        Args:
            file: The uploaded file (FastAPI UploadFile)
        """
        # Read the file content
        content = await file.read()
        file_size = len(content)
        filename = file.filename

        # In a real application, you might process the file, ingest it into a vector store, etc.
        # Here we just print some info to the console.
        print(f"Received file: {filename}, size: {file_size} bytes")

        # Note: The upload_handler doesn't return a response to the chat stream directly.
        # The frontend receives a success status.
        # If you want to notify the user in the chat, the user would usually send a message
        # mentioning they uploaded a file, or you could potentially trigger something else.
        # Currently the flow is: UI uploads -> Backend handles -> UI gets 200 OK.
