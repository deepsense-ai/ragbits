"""Unit tests for generic custom response functionality."""

# ruff: noqa: PLR6301
from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from ragbits.chat.interface.types import ChatResponse, ResponseContent


class TestCustomResponseCreation:
    """Test cases for creating custom responses using the generic approach."""

    def test_create_simple_custom_response(self):
        """Test creating a simple custom response with basic fields."""

        class SimpleContent(ResponseContent):
            """Simple test content."""

            message: str
            count: int

            def get_type(self) -> str:
                return "simple"

        class SimpleResponse(ChatResponse[SimpleContent]):
            """Simple test response."""

        # Create and verify
        content = SimpleContent(message="Hello", count=42)
        response = SimpleResponse(content=content)

        assert response.get_type() == "simple"
        assert response.content.message == "Hello"
        assert response.content.count == 42

    def test_create_complex_custom_response(self):
        """Test creating a complex custom response with validation."""

        class UserProfileContent(ResponseContent):
            """User profile content with validation."""

            name: str = Field(..., min_length=1)
            age: int = Field(..., ge=0, le=150)
            email: str = Field(..., pattern=r".+@.+\..+")
            is_active: bool = True

            def get_type(self) -> str:
                return "user_profile"

        class UserProfileResponse(ChatResponse[UserProfileContent]):
            """User profile response."""

        # Create and verify
        content = UserProfileContent(name="Alice", age=30, email="alice@example.com")
        response = UserProfileResponse(content=content)

        assert response.get_type() == "user_profile"
        assert response.content.name == "Alice"
        assert response.content.age == 30
        assert response.content.email == "alice@example.com"
        assert response.content.is_active is True

    def test_create_response_with_nested_structures(self):
        """Test creating a response with lists and nested data."""

        class MetadataModel(BaseModel):
            """Nested metadata model."""

            created_by: str
            timestamp: str

        class AnalyticsContent(ResponseContent):
            """Analytics content with nested structures."""

            labels: list[str]
            values: list[float]
            metadata: MetadataModel

            def get_type(self) -> str:
                return "analytics"

        class AnalyticsResponse(ChatResponse[AnalyticsContent]):
            """Analytics response."""

        # Create and verify
        metadata = MetadataModel(created_by="system", timestamp="2025-01-01T00:00:00Z")
        content = AnalyticsContent(labels=["A", "B", "C"], values=[10.5, 20.3, 30.7], metadata=metadata)
        response = AnalyticsResponse(content=content)

        assert response.get_type() == "analytics"
        assert len(response.content.labels) == 3
        assert response.content.labels[0] == "A"
        assert response.content.values[1] == 20.3
        assert response.content.metadata.created_by == "system"

    def test_create_response_with_literal_types(self):
        """Test creating a response with Literal type restrictions."""

        class ChartContent(ResponseContent):
            """Chart content with restricted types."""

            chart_type: Literal["line", "bar", "pie"]
            data: list[int]

            def get_type(self) -> str:
                return "chart"

        class ChartResponse(ChatResponse[ChartContent]):
            """Chart response."""

        # Valid chart type
        content = ChartContent(chart_type="line", data=[1, 2, 3])
        response = ChartResponse(content=content)

        assert response.get_type() == "chart"
        assert response.content.chart_type == "line"

    def test_create_response_with_optional_fields(self):
        """Test creating a response with optional fields."""

        class NotificationContent(ResponseContent):
            """Notification content with optional fields."""

            title: str
            message: str
            urgency: Literal["low", "medium", "high"] = "medium"
            link: str | None = None

            def get_type(self) -> str:
                return "notification"

        class NotificationResponse(ChatResponse[NotificationContent]):
            """Notification response."""

        # Without optional fields
        content1 = NotificationContent(title="Alert", message="Something happened")
        response1 = NotificationResponse(content=content1)

        assert response1.content.urgency == "medium"
        assert response1.content.link is None

        # With optional fields
        content2 = NotificationContent(title="Alert", message="Check this", urgency="high", link="https://example.com")
        response2 = NotificationResponse(content=content2)

        assert response2.content.urgency == "high"
        assert response2.content.link == "https://example.com"


class TestCustomResponseValidation:
    """Test cases for validation in custom responses."""

    def test_validation_fails_for_invalid_data(self):
        """Test that validation errors are raised for invalid data."""

        class StrictContent(ResponseContent):
            """Content with strict validation."""

            age: int = Field(..., ge=0, le=150)
            email: str = Field(..., pattern=r".+@.+\..+")

            def get_type(self) -> str:
                return "strict"

        # Invalid age
        with pytest.raises(ValidationError):
            StrictContent(age=200, email="valid@example.com")

        # Invalid email
        with pytest.raises(ValidationError):
            StrictContent(age=30, email="not-an-email")

    def test_validation_for_required_fields(self):
        """Test that required fields must be provided."""

        class RequiredContent(ResponseContent):
            """Content with required fields."""

            required_field: str

            def get_type(self) -> str:
                return "required"

        # Missing required field
        with pytest.raises(ValidationError):
            RequiredContent()  # type: ignore

    def test_validation_for_list_constraints(self):
        """Test validation of list constraints."""

        class ListContent(ResponseContent):
            """Content with list constraints."""

            items: list[str] = Field(..., min_length=1, max_length=5)

            def get_type(self) -> str:
                return "list"

        # Valid list
        content = ListContent(items=["a", "b", "c"])
        assert len(content.items) == 3

        # Empty list (invalid)
        with pytest.raises(ValidationError):
            ListContent(items=[])

        # Too many items (invalid)
        with pytest.raises(ValidationError):
            ListContent(items=["a", "b", "c", "d", "e", "f"])


class TestCustomResponseSerialization:
    """Test cases for serialization of custom responses."""

    def test_response_serialization_to_dict(self):
        """Test that custom responses can be serialized to dict."""

        class SimpleContent(ResponseContent):
            """Simple content."""

            text: str
            number: int

            def get_type(self) -> str:
                return "simple"

        class SimpleResponse(ChatResponse[SimpleContent]):
            """Simple response."""

        content = SimpleContent(text="Hello", number=42)
        response = SimpleResponse(content=content)

        # Serialize to dict
        data = response.model_dump()

        assert "content" in data
        assert data["content"]["text"] == "Hello"
        assert data["content"]["number"] == 42

    def test_response_serialization_to_json(self):
        """Test that custom responses can be serialized to JSON."""

        class DataContent(ResponseContent):
            """Data content."""

            values: list[int]
            metadata: dict[str, str]

            def get_type(self) -> str:
                return "data"

        class DataResponse(ChatResponse[DataContent]):
            """Data response."""

        content = DataContent(values=[1, 2, 3], metadata={"key": "value"})
        response = DataResponse(content=content)

        # Serialize to JSON
        json_str = response.model_dump_json()

        assert "values" in json_str
        assert "[1,2,3]" in json_str or "[1, 2, 3]" in json_str
        assert "metadata" in json_str
        assert "key" in json_str

    def test_response_deserialization_from_dict(self):
        """Test that custom responses can be deserialized from dict."""

        class SimpleContent(ResponseContent):
            """Simple content."""

            message: str

            def get_type(self) -> str:
                return "simple"

        class SimpleResponse(ChatResponse[SimpleContent]):
            """Simple response."""

        # Create from dict
        data = {"content": {"message": "Test"}}
        response = SimpleResponse.model_validate(data)

        assert response.content.message == "Test"
        assert response.get_type() == "simple"


class TestCustomResponseTypeIdentification:
    """Test cases for type identification in custom responses."""

    def test_get_type_returns_correct_identifier(self):
        """Test that get_type() returns the correct identifier."""

        class CustomContent(ResponseContent):
            """Custom content."""

            def get_type(self) -> str:
                return "my_custom_type"

        class CustomResponse(ChatResponse[CustomContent]):
            """Custom response."""

        content = CustomContent()
        response = CustomResponse(content=content)

        assert response.get_type() == "my_custom_type"
        assert response.content.get_type() == "my_custom_type"

    def test_different_responses_have_different_types(self):
        """Test that different response types return different identifiers."""

        class TypeAContent(ResponseContent):
            """Type A content."""

            def get_type(self) -> str:
                return "type_a"

        class TypeAResponse(ChatResponse[TypeAContent]):
            """Type A response."""

        class TypeBContent(ResponseContent):
            """Type B content."""

            def get_type(self) -> str:
                return "type_b"

        class TypeBResponse(ChatResponse[TypeBContent]):
            """Type B response."""

        response_a = TypeAResponse(content=TypeAContent())
        response_b = TypeBResponse(content=TypeBContent())

        assert response_a.get_type() == "type_a"
        assert response_b.get_type() == "type_b"
        assert response_a.get_type() != response_b.get_type()


class TestMultipleCustomResponses:
    """Test cases for multiple custom response types working together."""

    def test_multiple_custom_response_types_coexist(self):
        """Test that multiple custom response types can coexist."""

        class ProfileContent(ResponseContent):
            """Profile content."""

            name: str

            def get_type(self) -> str:
                return "profile"

        class StatsContent(ResponseContent):
            """Stats content."""

            count: int

            def get_type(self) -> str:
                return "stats"

        class SettingsContent(ResponseContent):
            """Settings content."""

            enabled: bool

            def get_type(self) -> str:
                return "settings"

        class ProfileResponse(ChatResponse[ProfileContent]):
            """Profile response."""

        class StatsResponse(ChatResponse[StatsContent]):
            """Stats response."""

        class SettingsResponse(ChatResponse[SettingsContent]):
            """Settings response."""

        # Create multiple different responses
        responses: list[ChatResponse[Any]] = [
            ProfileResponse(content=ProfileContent(name="Alice")),
            StatsResponse(content=StatsContent(count=100)),
            SettingsResponse(content=SettingsContent(enabled=True)),
        ]

        # Verify they're all distinct
        types = [r.get_type() for r in responses]
        assert types == ["profile", "stats", "settings"]
        assert len(set(types)) == 3  # All unique
