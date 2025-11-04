"""Unit tests for custom response functionality."""

# ruff: noqa: PLR6301
import pytest
from pydantic import BaseModel

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatResponse, ChatResponseType, Custom, Reference


class SampleUserProfile(BaseModel):
    """Sample Pydantic model for testing."""

    name: str
    age: int
    email: str


class TestCustomResponseCreation:
    """Test cases for creating custom responses."""

    def test_create_custom_response_with_pydantic_model(self):
        """Test creating a custom response with a Pydantic model."""
        profile = SampleUserProfile(name="Alice", age=30, email="alice@example.com")

        response = ChatInterface.create_custom_response(type="user_profile", content=profile)

        assert response.type == ChatResponseType.CUSTOM
        assert isinstance(response.content, Custom)
        assert response.content.type == "user_profile"
        assert isinstance(response.content.content, SampleUserProfile)
        assert response.content.content.name == "Alice"
        assert response.content.content.age == 30

    def test_create_custom_response_with_dict(self):
        """Test creating a custom response with a dictionary."""
        chart_data = {"labels": ["A", "B", "C"], "values": [10, 20, 30]}

        response = ChatInterface.create_custom_response(type="chart_data", content=chart_data)

        assert response.type == ChatResponseType.CUSTOM
        assert isinstance(response.content, Custom)
        assert response.content.type == "chart_data"
        assert response.content.content == chart_data

    def test_create_custom_response_with_list(self):
        """Test creating a custom response with a list."""
        items = ["item1", "item2", "item3"]

        response = ChatInterface.create_custom_response(type="item_list", content=items)

        assert response.type == ChatResponseType.CUSTOM
        assert isinstance(response.content, Custom)
        assert response.content.type == "item_list"
        assert response.content.content == items

    def test_create_custom_response_with_primitive_types(self):
        """Test creating custom responses with primitive types."""
        # Integer
        response_int = ChatInterface.create_custom_response(type="count", content=42)
        assert isinstance(response_int.content, Custom)
        assert response_int.content.content == 42

        # String
        response_str = ChatInterface.create_custom_response(type="status", content="active")
        assert isinstance(response_str.content, Custom)
        assert response_str.content.content == "active"

        # Boolean
        response_bool = ChatInterface.create_custom_response(type="enabled", content=True)
        assert isinstance(response_bool.content, Custom)
        assert response_bool.content.content is True

        # Float
        response_float = ChatInterface.create_custom_response(type="percentage", content=75.5)
        assert isinstance(response_float.content, Custom)
        assert response_float.content.content == 75.5

        # None
        response_none = ChatInterface.create_custom_response(type="empty", content=None)
        assert isinstance(response_none.content, Custom)
        assert response_none.content.content is None

    def test_create_custom_response_with_nested_structure(self):
        """Test creating a custom response with nested dictionaries and lists."""
        nested_data = {
            "user": {"name": "Bob", "id": 123},
            "scores": [85, 92, 78],
            "metadata": {"created": "2025-01-01", "active": True},
        }

        response = ChatInterface.create_custom_response(type="nested_data", content=nested_data)

        assert response.type == ChatResponseType.CUSTOM
        assert isinstance(response.content, Custom)
        assert response.content.content == nested_data
        assert isinstance(response.content.content, dict)
        assert response.content.content["user"]["name"] == "Bob"
        assert response.content.content["scores"][1] == 92


class TestCustomResponseValidation:
    """Test cases for custom response validation."""

    def test_invalid_content_raises_error(self):
        """Test that non-JSON-serializable content raises a validation error."""

        class NonSerializable:
            def __init__(self):
                self.data = "test"

        with pytest.raises(ValueError, match="must be JSON-serializable"):
            ChatInterface.create_custom_response(type="invalid", content=NonSerializable())

    def test_function_content_raises_error(self):
        """Test that function content raises a validation error."""

        def my_function() -> str:
            return "test"

        with pytest.raises(ValueError, match="must be JSON-serializable"):
            ChatInterface.create_custom_response(type="invalid", content=my_function)

    def test_complex_object_raises_error(self):
        """Test that complex non-serializable objects raise validation errors."""
        import datetime

        # datetime objects are not JSON-serializable without custom encoder
        with pytest.raises(ValueError, match="must be JSON-serializable"):
            ChatInterface.create_custom_response(type="invalid", content=datetime.datetime.now())


class TestCustomResponseAccessor:
    """Test cases for the as_custom() accessor method."""

    def test_as_custom_returns_custom_for_custom_response(self):
        """Test that as_custom() returns Custom object for custom responses."""
        response = ChatInterface.create_custom_response(type="test", content={"key": "value"})

        custom = response.as_custom()

        assert custom is not None
        assert isinstance(custom, Custom)
        assert custom.type == "test"
        assert custom.content == {"key": "value"}

    def test_as_custom_returns_none_for_non_custom_response(self):
        """Test that as_custom() returns None for non-custom responses."""
        text_response = ChatResponse(type=ChatResponseType.TEXT, content="Hello")

        custom = text_response.as_custom()

        assert custom is None

    def test_as_custom_with_different_response_types(self):
        """Test that as_custom() correctly returns None for various other response types."""
        # Test with different response types
        reference_response = ChatResponse(
            type=ChatResponseType.REFERENCE,
            content=Reference(title="Doc", content="Content", url="http://example.com"),
        )
        assert reference_response.as_custom() is None

        message_id_response = ChatResponse(type=ChatResponseType.MESSAGE_ID, content="msg-123")
        assert message_id_response.as_custom() is None

        clear_response = ChatResponse(type=ChatResponseType.CLEAR_MESSAGE, content=None)
        assert clear_response.as_custom() is None


class TestCustomModel:
    """Test cases for the Custom Pydantic model itself."""

    def test_custom_model_with_valid_json_types(self):
        """Test Custom model accepts valid JSON-serializable types."""
        # Dict
        custom1 = Custom(type="test1", content={"key": "value"})
        assert custom1.content == {"key": "value"}

        # List
        custom2 = Custom(type="test2", content=[1, 2, 3])
        assert custom2.content == [1, 2, 3]

        # String
        custom3 = Custom(type="test3", content="text")
        assert custom3.content == "text"

        # Number
        custom4 = Custom(type="test4", content=42)
        assert custom4.content == 42

        # Boolean
        custom5 = Custom(type="test5", content=True)
        assert custom5.content is True

        # None
        custom6 = Custom(type="test6", content=None)
        assert custom6.content is None

    def test_custom_model_with_pydantic_model(self):
        """Test Custom model accepts Pydantic BaseModel instances."""
        profile = SampleUserProfile(name="Charlie", age=35, email="charlie@example.com")
        custom = Custom(type="profile", content=profile)

        assert isinstance(custom.content, SampleUserProfile)
        assert custom.content.name == "Charlie"

    def test_custom_model_serialization(self):
        """Test that Custom model can be serialized to dict/JSON."""
        profile = SampleUserProfile(name="Dave", age=40, email="dave@example.com")
        custom = Custom(type="profile", content=profile)

        # Test model_dump
        dumped = custom.model_dump()
        assert dumped["type"] == "profile"
        assert dumped["content"]["name"] == "Dave"
        assert dumped["content"]["age"] == 40

        # Test model_dump_json
        json_str = custom.model_dump_json()
        assert "Dave" in json_str
        assert "profile" in json_str
