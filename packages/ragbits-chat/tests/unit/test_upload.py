from collections.abc import AsyncGenerator

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from ragbits.chat.api import RagbitsAPI
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, TextContent, TextResponse
from ragbits.core.prompt import ChatFormat


class MockChat(ChatInterface):
    """Mock ChatInterface for testing."""

    async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator:  # noqa: PLR6301
        """Mock chat implementation."""
        yield TextResponse(content=TextContent(text=message))


def test_upload_disabled() -> None:
    """Test that upload/ endpoint returns 400 when no handler is configured."""
    api = RagbitsAPI(chat_interface=MockChat)
    client = TestClient(api.app)

    files = {"file": ("test.txt", b"content")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "File upload not supported"


@pytest.mark.asyncio
async def test_upload_enabled() -> None:
    """Test that upload/ endpoint works when a handler is configured."""
    uploaded_content = None

    async def handle_upload(self: ChatInterface, file: UploadFile) -> None:
        nonlocal uploaded_content
        uploaded_content = await file.read()

    # Define subclass with proper handler.
    # Must use a fresh class to avoid closure issues if multiple tests ran.
    class MockChatWithUpload(MockChat):
        """Mock ChatInterface with upload handler."""

    from typing import Any, cast

    MockChatWithUpload.upload_handler = cast(Any, handle_upload)

    api = RagbitsAPI(chat_interface=MockChatWithUpload)
    client = TestClient(api.app)

    files = {"file": ("test.txt", b"hello world")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "filename": "test.txt"}
    assert uploaded_content == b"hello world"
