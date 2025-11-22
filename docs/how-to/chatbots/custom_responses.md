# How-To: Create Custom Response Types for Chat Interfaces

This guide shows you how to create custom response types for your Ragbits chat applications using the generic `ChatResponse` and `ResponseContent` system.

## Overview

Custom response types allow you to send structured, typed data from your chat backend to your frontend. This is useful for:

- **Analytics and Charts**: Send visualization data directly from your chat
- **User Profiles**: Return structured user information
- **Forms and Interactive Elements**: Send interactive components
- **Custom Data Structures**: Any application-specific data that needs type safety

The custom response system provides:
- **Full Type Safety**: Complete IDE autocomplete and type checking
- **Automatic Validation**: Pydantic validates all fields automatically
- **Easy Serialization**: Seamless JSON conversion for API transmission
- **Frontend Integration**: Type identifiers help frontends render responses correctly

## Basic Concept

Creating a custom response involves two steps:

1. **Define a Content Class**: Extend `ResponseContent` to specify your data structure
2. **Define a Response Class**: Extend `ChatResponse[YourContent]` to wrap the content

The `ResponseContent` class must implement a `get_type()` method that returns a unique string identifier. This identifier is used by frontend clients to determine how to render the response.

## Simple Example

Here's a basic example of creating a custom user profile response:

```python
from pydantic import Field
from ragbits.chat.interface.types import ResponseContent, ChatResponse

# Step 1: Define the content structure
class UserProfileContent(ResponseContent):
    """User profile information."""

    name: str = Field(..., min_length=1, description="User's full name")
    age: int = Field(..., ge=0, le=150, description="User's age")
    email: str = Field(..., description="User's email address")
    bio: str | None = Field(default=None, description="Optional biography")

    def get_type(self) -> str:
        """Return unique type identifier."""
        return "user_profile"

# Step 2: Define the response wrapper
class UserProfileResponse(ChatResponse[UserProfileContent]):
    """User profile response for streaming to clients."""
```

## Using Custom Responses in Your Chat

To use your custom response in a chat interface, simply yield it from your `chat()` method:

```python
from collections.abc import AsyncGenerator
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.prompt import ChatFormat

class MyChat(ChatInterface):
    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Create some text response first
        yield self.create_text_response("Here's the user profile:")

        # Send the custom user profile
        profile = UserProfileContent(
            name="Alice Johnson",
            age=28,
            email="alice@example.com",
            bio="Software engineer passionate about AI"
        )
        yield UserProfileResponse(content=profile)
```

## Advanced Examples

### Example 1: Chart/Analytics Data

Send structured chart data for visualization:

```python
from typing import Literal
from pydantic import Field
from ragbits.chat.interface.types import ResponseContent, ChatResponse

class ChartDataContent(ResponseContent):
    """Chart visualization data."""

    labels: list[str] = Field(..., description="X-axis labels")
    values: list[float] = Field(..., description="Y-axis values")
    chart_type: Literal["line", "bar", "pie", "scatter"] = Field(
        default="line",
        description="Type of chart to render"
    )
    title: str = Field(..., description="Chart title")

    def get_type(self) -> str:
        return "chart_data"

class ChartDataResponse(ChatResponse[ChartDataContent]):
    """Chart data response."""

# Usage
chart = ChartDataContent(
    labels=["Q1", "Q2", "Q3", "Q4"],
    values=[100.5, 150.2, 120.0, 180.3],
    chart_type="bar",
    title="Quarterly Revenue ($M)"
)
yield ChartDataResponse(content=chart)
```

### Example 2: Notification with Urgency

Create a notification system with different urgency levels:

```python
from typing import Literal
from pydantic import Field, HttpUrl
from ragbits.chat.interface.types import ResponseContent, ChatResponse

class NotificationContent(ResponseContent):
    """Notification with urgency level."""

    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    urgency: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Urgency level"
    )
    action_url: HttpUrl | None = Field(
        default=None,
        description="Optional URL for action button"
    )
    action_label: str | None = Field(
        default=None,
        description="Label for the action button"
    )

    def get_type(self) -> str:
        return "notification"

class NotificationResponse(ChatResponse[NotificationContent]):
    """Notification response."""

# Usage
notification = NotificationContent(
    title="Security Alert",
    message="Unusual login detected from new location",
    urgency="high",
    action_url="https://example.com/security/review",
    action_label="Review Activity"
)
yield NotificationResponse(content=notification)
```

### Example 3: Complex Nested Structures

Use nested Pydantic models for complex data:

```python
from pydantic import BaseModel, Field
from ragbits.chat.interface.types import ResponseContent, ChatResponse

class Address(BaseModel):
    """Address information."""
    street: str
    city: str
    country: str
    postal_code: str

class ContactInfo(BaseModel):
    """Contact information."""
    email: str
    phone: str | None = None
    linkedin: str | None = None

class DetailedProfileContent(ResponseContent):
    """Detailed user profile with nested structures."""

    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0, le=150)
    addresses: list[Address] = Field(default_factory=list)
    contact: ContactInfo
    skills: list[str] = Field(default_factory=list)
    experience_years: int = Field(..., ge=0)

    def get_type(self) -> str:
        return "detailed_profile"

class DetailedProfileResponse(ChatResponse[DetailedProfileContent]):
    """Detailed profile response."""

# Usage
profile = DetailedProfileContent(
    name="Bob Smith",
    age=35,
    addresses=[
        Address(
            street="123 Main St",
            city="San Francisco",
            country="USA",
            postal_code="94102"
        )
    ],
    contact=ContactInfo(
        email="bob@example.com",
        phone="+1-555-0123",
        linkedin="linkedin.com/in/bobsmith"
    ),
    skills=["Python", "Machine Learning", "Cloud Architecture"],
    experience_years=12
)
yield DetailedProfileResponse(content=profile)
```

### Example 4: Form/Interactive Element

Send a form definition for user interaction:

```python
from pydantic import BaseModel, Field
from ragbits.chat.interface.types import ResponseContent, ChatResponse
from typing import Literal

class FormField(BaseModel):
    """Single form field definition."""
    name: str
    label: str
    field_type: Literal["text", "email", "number", "select", "textarea"]
    required: bool = True
    options: list[str] | None = None  # For select fields
    placeholder: str | None = None

class FormContent(ResponseContent):
    """Interactive form definition."""

    form_id: str = Field(..., description="Unique form identifier")
    title: str = Field(..., description="Form title")
    description: str | None = Field(default=None, description="Form description")
    fields: list[FormField] = Field(..., description="Form fields")
    submit_label: str = Field(default="Submit", description="Submit button label")

    def get_type(self) -> str:
        return "form"

class FormResponse(ChatResponse[FormContent]):
    """Form response."""

# Usage
form = FormContent(
    form_id="user_feedback_001",
    title="Provide Feedback",
    description="Help us improve by sharing your thoughts",
    fields=[
        FormField(
            name="rating",
            label="How would you rate your experience?",
            field_type="select",
            options=["Excellent", "Good", "Fair", "Poor"]
        ),
        FormField(
            name="comments",
            label="Additional comments",
            field_type="textarea",
            required=False,
            placeholder="Share your thoughts..."
        ),
        FormField(
            name="email",
            label="Email (optional)",
            field_type="email",
            required=False
        )
    ]
)
yield FormResponse(content=form)
```

## Validation and Type Safety

Pydantic automatically validates all fields. Here's how to add custom validation:

```python
from pydantic import Field, field_validator, model_validator
from ragbits.chat.interface.types import ResponseContent, ChatResponse

class ProductContent(ResponseContent):
    """Product information with validation."""

    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0, description="Price must be positive")
    quantity: int = Field(..., ge=0, description="Quantity in stock")
    discount_percent: float = Field(default=0, ge=0, le=100)

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode='after')
    def check_discount_logic(self):
        """Ensure discount makes sense."""
        if self.discount_percent > 0 and self.quantity == 0:
            raise ValueError("Cannot have discount on out-of-stock items")
        return self

    def get_type(self) -> str:
        return "product"

class ProductResponse(ChatResponse[ProductContent]):
    """Product response."""
```

## Best Practices

### 1. Use Descriptive Type Identifiers

Choose clear, unique identifiers for `get_type()`:

```python
def get_type(self) -> str:
    return "user_profile"  # Good: clear and specific
    # return "data"  # Bad: too generic
    # return "userProfile"  # Avoid: use snake_case for consistency
```

### 2. Add Field Descriptions

Always document your fields for better API documentation:

```python
class DataContent(ResponseContent):
    value: int = Field(..., description="The computed value")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
```

### 3. Use Type Hints and Validation

Leverage Pydantic's validation features:

```python
from pydantic import Field, EmailStr, HttpUrl

class ContactContent(ResponseContent):
    email: EmailStr  # Validates email format
    website: HttpUrl  # Validates URL format
    age: int = Field(..., ge=18, le=120)  # Age constraints
    tags: list[str] = Field(..., min_length=1, max_length=10)
```

### 4. Consider Optional Fields with Defaults

Make fields optional when appropriate:

```python
class EventContent(ResponseContent):
    title: str  # Required
    description: str | None = None  # Optional
    priority: Literal["low", "medium", "high"] = "medium"  # Optional with default
```

### 5. Group Related Custom Responses

Organize custom responses in a separate module:

```python
# my_app/responses.py
from ragbits.chat.interface.types import ResponseContent, ChatResponse

class UserProfileContent(ResponseContent):
    # ... implementation ...
    def get_type(self) -> str:
        return "user_profile"

class UserProfileResponse(ChatResponse[UserProfileContent]):
    pass

class ChartDataContent(ResponseContent):
    # ... implementation ...
    def get_type(self) -> str:
        return "chart_data"

class ChartDataResponse(ChatResponse[ChartDataContent]):
    pass
```

## Testing Custom Responses

Here's how to test your custom responses:

```python
import pytest
from pydantic import ValidationError

def test_user_profile_creation():
    """Test creating a valid user profile."""
    content = UserProfileContent(
        name="Alice",
        age=30,
        email="alice@example.com"
    )
    response = UserProfileResponse(content=content)

    assert response.get_type() == "user_profile"
    assert response.content.name == "Alice"
    assert response.content.age == 30

def test_user_profile_validation():
    """Test validation failures."""
    # Invalid age
    with pytest.raises(ValidationError):
        UserProfileContent(
            name="Bob",
            age=200,  # Too old
            email="bob@example.com"
        )

    # Missing required field
    with pytest.raises(ValidationError):
        UserProfileContent(
            name="Charlie",
            age=25
            # Missing email
        )

def test_response_serialization():
    """Test serializing response to JSON."""
    content = UserProfileContent(
        name="David",
        age=28,
        email="david@example.com"
    )
    response = UserProfileResponse(content=content)

    # Serialize to dict
    data = response.model_dump()
    assert "content" in data
    assert data["content"]["name"] == "David"

    # Serialize to JSON string
    json_str = response.model_dump_json()
    assert "David" in json_str
```

## Frontend Integration

When you send a custom response, it's serialized to JSON like this:

```json
{
  "content": {
    "name": "Alice Johnson",
    "age": 28,
    "email": "alice@example.com",
    "bio": "Software engineer passionate about AI"
  }
}
```

The frontend can use the response type to determine how to render it. In TypeScript:

```typescript
// Handle incoming chat responses
function handleChatResponse(response: ChatResponse) {
  const type = response.content.type; // From get_type()

  switch (type) {
    case 'user_profile':
      renderUserProfile(response.content);
      break;
    case 'chart_data':
      renderChart(response.content);
      break;
    case 'notification':
      showNotification(response.content);
      break;
    // ... handle other types
  }
}
```

## Complete Example

Here's a complete working example that demonstrates multiple custom response types:

```python
from collections.abc import AsyncGenerator
from typing import Literal
from pydantic import Field
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import (
    ChatContext,
    ChatResponse,
    ResponseContent,
)
from ragbits.core.prompt import ChatFormat
from ragbits.core.llms import LiteLLM

# Define custom response types
class AnalyticsContent(ResponseContent):
    """Analytics dashboard data."""
    total_users: int = Field(..., ge=0)
    active_users: int = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    growth_rate: float

    def get_type(self) -> str:
        return "analytics"

class AnalyticsResponse(ChatResponse[AnalyticsContent]):
    """Analytics response."""

class AlertContent(ResponseContent):
    """System alert."""
    severity: Literal["info", "warning", "error", "critical"]
    message: str
    timestamp: str

    def get_type(self) -> str:
        return "alert"

class AlertResponse(ChatResponse[AlertContent]):
    """Alert response."""

# Use in chat interface
class DashboardChat(ChatInterface):
    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Check what the user is asking for
        message_lower = message.lower()

        if "analytics" in message_lower or "dashboard" in message_lower:
            yield self.create_text_response("Here's your analytics dashboard:")

            # Send custom analytics data
            analytics = AnalyticsContent(
                total_users=15234,
                active_users=8456,
                revenue=125430.50,
                growth_rate=0.127
            )
            yield AnalyticsResponse(content=analytics)

        elif "alert" in message_lower or "warning" in message_lower:
            yield self.create_text_response("System Status:")

            # Send custom alert
            alert = AlertContent(
                severity="warning",
                message="Database connection pool at 85% capacity",
                timestamp="2025-11-22T10:30:00Z"
            )
            yield AlertResponse(content=alert)

        else:
            # Default: use LLM for general conversation
            async for chunk in self.llm.generate_streaming(
                [*history, {"role": "user", "content": message}]
            ):
                yield self.create_text_response(chunk)
```

Run this chat application:

```bash
ragbits api run dashboard_chat:DashboardChat
```

## Migration from Old Response Types

If you're using the deprecated `ChatResponseType` enum, here's how to migrate:

**Old code:**
```python
if response.type == ChatResponseType.TEXT:
    text = response.as_text()
    print(text)
```

**New code:**
```python
from ragbits.chat.interface.types import TextResponse

if isinstance(response, TextResponse):
    text = response.content.text
    print(text)
```

The old API is deprecated but still works for backward compatibility.

## Summary

Custom response types in Ragbits provide a powerful way to send structured, validated data from your chat backend to your frontend. Key takeaways:

1. Extend `ResponseContent` and implement `get_type()` for your content
2. Extend `ChatResponse[YourContent]` to create the response wrapper
3. Use Pydantic features for validation and type safety
4. Yield custom responses from your `chat()` method
5. Frontend uses the type identifier to render responses appropriately

This approach gives you full type safety, automatic validation, and seamless integration with your chat interface.
