# Custom Response Types Example

This directory contains examples demonstrating how to create and use custom response types in Ragbits Chat.

## Overview

Custom response types allow you to send structured, typed data from your chat backend to your frontend. Instead of just sending text, you can send:

- **Analytics dashboards** with metrics and KPIs
- **Product catalogs** with rich product information
- **System notifications** with different severity levels
- **Interactive forms** for collecting user input
- **Location data** for map displays
- Any custom data structure your application needs

## Files

### `custom_responses_example.py`

A comprehensive example showing multiple custom response types:

- `AnalyticsSummaryContent`: Dashboard metrics (visitors, page views, conversion rates, etc.)
- `ProductContent`: E-commerce product information
- `NotificationContent`: System alerts and notifications
- `InteractiveFormContent`: Dynamic forms for user input
- `LocationContent`: Geographic location data for maps

**Run it:**
```bash
ragbits api run custom_responses_example:CustomResponseChat
```

**Try these commands in the chat:**
- "show me analytics" - See dashboard metrics
- "show me products" - Browse product catalog
- "show me alerts" - View system notifications
- "show me a form" - See an interactive form
- "show me locations" - View location data

### `simple_custom_response.py`

A minimal example showing the basics of custom responses:

- `UserProfileContent`: Simple user profile with name, age, and email
- `ChartDataContent`: Basic chart data with labels and values

**Run it:**
```bash
ragbits api run simple_custom_response:SimpleCustomChat
```

## Key Concepts

### 1. Define Content Class

Extend `ResponseContent` and implement `get_type()`:

```python
from pydantic import Field
from ragbits.chat.interface.types import ResponseContent

class MyContent(ResponseContent):
    """My custom content."""

    field1: str = Field(..., description="Field description")
    field2: int = Field(..., ge=0)

    def get_type(self) -> str:
        return "my_custom_type"
```

### 2. Define Response Class

Extend `ChatResponse[YourContent]`:

```python
from ragbits.chat.interface.types import ChatResponse

class MyResponse(ChatResponse[MyContent]):
    """My custom response."""
```

### 3. Use in Chat

Yield the custom response from your `chat()` method:

```python
async def chat(self, message: str, history: ChatFormat, context: ChatContext):
    # Create content
    content = MyContent(field1="value", field2=42)

    # Yield response
    yield MyResponse(content=content)
```

## Benefits

- **Type Safety**: Full IDE autocomplete and type checking
- **Validation**: Pydantic validates all fields automatically
- **Serialization**: Automatic JSON conversion for API transmission
- **Frontend Integration**: Type identifiers help frontends render responses correctly

## Frontend Integration

When you send a custom response, it's serialized to JSON:

```json
{
  "content": {
    "field1": "value",
    "field2": 42
  }
}
```

The `get_type()` method provides a type identifier that frontends can use to determine how to render the data.

## Documentation

For more details, see the full tutorial:
- [How-To: Create Custom Response Types](../../docs/how-to/chatbots/custom_responses.md)

## Requirements

- Python 3.10+
- ragbits-chat package
- LiteLLM (for the LLM-based examples)

## Related Examples

- `chat.py` - Basic chat example with custom responses
- `tutorial.py` - Tutorial-style chat example
- `authenticated_chat.py` - Chat with authentication

## Support

For questions or issues:
- Documentation: https://ragbits.deepsense.ai/
- GitHub Issues: https://github.com/deepsense-ai/ragbits/issues
