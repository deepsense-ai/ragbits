"""Unit tests for ErrorContent and ErrorResponse types."""

# ruff: noqa: PLR6301

import pytest
from pydantic import ValidationError

from ragbits.chat.interface.types import (
    ChatResponseType,
    ErrorContent,
    ErrorResponse,
)


class TestErrorContent:
    """Test cases for ErrorContent class."""

    def test_create_error_content_with_message(self):
        """Test creating ErrorContent with a message."""
        content = ErrorContent(message="Something went wrong")

        assert content.message == "Something went wrong"

    def test_get_type_returns_error(self):
        """Test that get_type() returns 'error'."""
        content = ErrorContent(message="Test error")

        assert content.get_type() == "error"

    def test_error_content_requires_message(self):
        """Test that message field is required."""
        with pytest.raises(ValidationError):
            ErrorContent()  # type: ignore

    def test_error_content_message_must_be_string(self):
        """Test that message must be a string."""
        with pytest.raises(ValidationError):
            ErrorContent(message=123)  # type: ignore

    def test_error_content_empty_message(self):
        """Test that empty message is allowed."""
        content = ErrorContent(message="")
        assert content.message == ""


class TestErrorResponse:
    """Test cases for ErrorResponse class."""

    def test_create_error_response(self):
        """Test creating ErrorResponse with ErrorContent."""
        content = ErrorContent(message="An error occurred")
        response = ErrorResponse(content=content)

        assert response.content.message == "An error occurred"

    def test_error_response_get_type(self):
        """Test that ErrorResponse.get_type() returns 'error'."""
        content = ErrorContent(message="Test")
        response = ErrorResponse(content=content)

        assert response.get_type() == "error"

    def test_error_response_serialization(self):
        """Test that ErrorResponse can be serialized to dict."""
        content = ErrorContent(message="Serialization test")
        response = ErrorResponse(content=content)

        data = response.model_dump()

        assert "content" in data
        assert data["content"]["message"] == "Serialization test"

    def test_error_response_json_serialization(self):
        """Test that ErrorResponse can be serialized to JSON."""
        content = ErrorContent(message="JSON test")
        response = ErrorResponse(content=content)

        json_str = response.model_dump_json()

        assert "message" in json_str
        assert "JSON test" in json_str

    def test_error_response_deserialization(self):
        """Test that ErrorResponse can be deserialized from dict."""
        data = {"content": {"message": "Deserialized error"}}
        response = ErrorResponse.model_validate(data)

        assert response.content.message == "Deserialized error"
        assert response.get_type() == "error"


class TestErrorResponseTypeEnum:
    """Test cases for ERROR in ChatResponseType enum."""

    def test_error_enum_value_exists(self):
        """Test that ERROR value exists in ChatResponseType."""
        assert hasattr(ChatResponseType, "ERROR")
        assert ChatResponseType.ERROR.value == "error"

    def test_error_enum_matches_content_type(self):
        """Test that ERROR enum value matches ErrorContent.get_type()."""
        content = ErrorContent(message="Test")
        assert ChatResponseType.ERROR.value == content.get_type()
