import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

from ragbits.chat.api import RagbitsAPI
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, FeedbackForm, FormField
from ragbits.chat.interface.types import ChatContext, ChatResponse, ChatResponseType, Reference


class MockChatInterface(ChatInterface):
    """A mock implementation of ChatInterface for testing."""

    def __init__(self) -> None:
        self.feedback_config = FeedbackConfig()

    async def chat(
        self, message: str, history: list[Any] | None = None, context: ChatContext | None = None
    ) -> AsyncGenerator[ChatResponse, None]:
        """Mock implementation that yields test responses."""
        yield self.create_text_response("Test response")
        yield self.create_reference(title="Test Reference", content="Test content", url="http://test.com")


@pytest.fixture
def mock_chat_interface() -> type[MockChatInterface]:
    """Fixture providing the MockChatInterface class."""
    return MockChatInterface


@pytest.fixture
def api(mock_chat_interface: type[MockChatInterface]) -> RagbitsAPI:
    """Fixture providing a RagbitsAPI instance with the mock interface."""
    api = RagbitsAPI(mock_chat_interface)
    return api


@pytest.fixture
def client(api: RagbitsAPI) -> TestClient:
    """Fixture providing a test client for the FastAPI app."""
    return TestClient(api.app)


@pytest.mark.asyncio
async def test_chat_response_to_sse() -> None:
    """Test conversion of chat responses to SSE format."""

    async def mock_generator() -> AsyncGenerator[ChatResponse, None]:
        yield ChatResponse(type=ChatResponseType.TEXT, content="Hello")
        yield ChatResponse(
            type=ChatResponseType.REFERENCE, content=Reference(title="Ref", content="Content", url="http://example.com")
        )

    sse_generator = RagbitsAPI._chat_response_to_sse(mock_generator())

    responses = []
    async for response in sse_generator:
        responses.append(response)

    # Should now have 2 chat responses
    assert len(responses) == 2

    # Second should be the text response
    assert responses[0] == 'data: {"type": "text", "content": "Hello"}\n\n'

    # Parse the second response JSON to check it
    second_response = responses[1].replace("data: ", "").strip()
    data = json.loads(second_response)
    assert data["type"] == "reference"
    assert data["content"]["title"] == "Ref"
    assert data["content"]["content"] == "Content"
    assert data["content"]["url"] == "http://example.com"


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint returns the index.html content."""
    with patch("builtins.open", mock_open(read_data="<html>Test</html>")):
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "<html>Test</html>"


def test_chat_endpoint(client: TestClient) -> None:
    """Test the chat endpoint returns streaming response."""
    request_data = {
        "message": "Hello",
        "history": [{"role": "user", "content": "Previous message"}],
        "context": {"user_id": "test_user"},
    }

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 200
    # Check only the main part of the content type, ignoring charset
    assert response.headers["content-type"].startswith("text/event-stream")

    # Test the content of the streamed response
    content = response.content.decode("utf-8")
    assert 'data: {"type": "text", "content": "Test response"}' in content
    assert 'data: {"type": "reference", "content": {"title": "Test Reference"' in content


def test_config_endpoint_with_feedback(client: TestClient, api: RagbitsAPI) -> None:
    """Test the config endpoint with feedback configuration enabled."""
    # Create properly structured feedback forms
    like_form = FeedbackForm(
        title="Like Feedback",
        fields=[
            FormField(
                name="like_reason", type="text", required=True, label="Why did you like this response?", options=None
            )
        ],
    )

    dislike_form = FeedbackForm(
        title="Dislike Feedback",
        fields=[
            FormField(
                name="dislike_reason",
                type="text",
                required=True,
                label="Why did you dislike this response?",
                options=None,
            )
        ],
    )

    # Set up feedback config
    api.chat_interface.feedback_config = FeedbackConfig(
        like_enabled=True, dislike_enabled=True, like_form=like_form, dislike_form=dislike_form
    )

    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()

    assert "feedback" in data
    assert "like" in data["feedback"]
    assert "dislike" in data["feedback"]
    assert data["feedback"]["like"]["enabled"] is True
    assert data["feedback"]["dislike"]["enabled"] is True
    assert data["feedback"]["like"]["form"]["fields"][0]["name"] == "like_reason"
    assert data["feedback"]["dislike"]["form"]["fields"][0]["name"] == "dislike_reason"


def test_config_endpoint_without_feedback(client: TestClient) -> None:
    """Test the config endpoint with feedback configuration disabled."""
    # Default MockChatInterface has feedback disabled
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "feedback" in data
    assert data["feedback"]["like"]["enabled"] is False
    assert data["feedback"]["dislike"]["enabled"] is False
    assert data["feedback"]["like"]["form"] is None
    assert data["feedback"]["dislike"]["form"] is None


def test_validation_exception_handler(client: TestClient) -> None:
    """Test handling of validation errors."""
    # Missing required 'message' field should trigger validation error
    response = client.post("/api/chat", json={})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "body" in data


def test_load_chat_interface_from_class() -> None:
    """Test loading chat interface from a class."""
    api = RagbitsAPI(MockChatInterface)
    assert isinstance(api.chat_interface, MockChatInterface)


@patch("importlib.import_module")
def test_load_chat_interface_from_string(mock_import: MagicMock) -> None:
    """Test loading chat interface from a string path."""

    class TestChatInterface(ChatInterface):
        async def chat(
            self, message: str, history: list[Any] | None = None, context: ChatContext | None = None
        ) -> AsyncGenerator[ChatResponse, None]:
            yield self.create_text_response("Test")

    mock_module = MagicMock()
    mock_module.TestClass = TestChatInterface
    mock_import.return_value = mock_module

    api = RagbitsAPI("test_module:TestClass")
    mock_import.assert_called_once_with("test_module")
    assert isinstance(api.chat_interface, TestChatInterface)


def test_state_verification_successful(client: TestClient, api: RagbitsAPI) -> None:
    """Test state verification succeeds with valid signature."""
    state = {"user_data": "test_value"}
    signature = api.chat_interface._sign_state(state)

    request_data = {
        "message": "Hello",
        "history": [{"role": "user", "content": "Previous message"}],
        "context": {"state": state, "signature": signature},
    }

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_state_verification_failed(client: TestClient, api: RagbitsAPI) -> None:
    """Test state verification fails with invalid signature."""
    state = {"user_data": "test_value"}
    invalid_signature = "invalid-signature"

    request_data = {
        "message": "Hello",
        "history": [{"role": "user", "content": "Previous message"}],
        "context": {"state": state, "signature": invalid_signature},
    }

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid state signature"


def test_load_chat_interface_invalid_type() -> None:
    """Test error when loading an invalid chat interface type."""

    class InvalidClass:
        pass

    with pytest.raises(TypeError, match="Implementation must inherit from ChatInterface"):
        RagbitsAPI(InvalidClass)  # type: ignore


def test_run_method() -> None:
    """Test the run method starts the uvicorn server."""
    api = RagbitsAPI(MockChatInterface)

    # Mock the uvicorn.run method
    with patch("uvicorn.run") as mock_run:
        api.run(host="localhost", port=9000)

        # Verify uvicorn.run was called with the correct parameters
        mock_run.assert_called_once_with(api.app, host="localhost", port=9000)
