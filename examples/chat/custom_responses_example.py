"""
Example demonstrating custom response types in Ragbits Chat.

This example shows how to create and use custom response types for sending
structured data from your chat backend to your frontend. We demonstrate:

1. Analytics dashboard data
2. Product catalog items
3. System notifications
4. Interactive forms
5. Location/map data

Run with:
    ragbits api run custom_responses_example:CustomResponseChat
"""

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, ResponseContent
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import ChatFormat


# ============================================================================
# Analytics Response
# ============================================================================
class AnalyticsSummaryContent(ResponseContent):
    """Analytics dashboard summary with key metrics.

    Use this to send analytics data that can be visualized as charts or cards.
    """

    total_visitors: int = Field(..., ge=0, description="Total number of visitors")
    page_views: int = Field(..., ge=0, description="Total page views")
    bounce_rate: float = Field(..., ge=0, le=1, description="Bounce rate (0-1)")
    avg_session_duration: float = Field(..., ge=0, description="Average session duration in seconds")
    conversion_rate: float = Field(..., ge=0, le=1, description="Conversion rate (0-1)")
    revenue: float = Field(..., ge=0, description="Total revenue")
    currency: str = Field(default="USD", description="Currency code")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content."""
        return "analytics_summary"


class AnalyticsSummaryResponse(ChatResponse[AnalyticsSummaryContent]):
    """Analytics summary response for streaming to clients."""


# ============================================================================
# Product Catalog Response
# ============================================================================
class ProductContent(ResponseContent):
    """Product information for e-commerce applications."""

    id: str = Field(..., description="Unique product ID")
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., gt=0, description="Product price")
    currency: str = Field(default="USD", description="Currency code")
    image_url: HttpUrl | None = Field(default=None, description="Product image URL")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(default=True, description="Stock availability")
    rating: float = Field(default=0, ge=0, le=5, description="Average rating (0-5)")
    tags: list[str] = Field(default_factory=list, description="Product tags")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content."""
        return "product"


class ProductResponse(ChatResponse[ProductContent]):
    """Product response for streaming to clients."""


# ============================================================================
# Notification Response
# ============================================================================
class NotificationContent(ResponseContent):
    """System notification with severity level.

    Use this to send alerts, warnings, or informational messages that should
    be displayed prominently in the UI.
    """

    title: str = Field(..., min_length=1, description="Notification title")
    message: str = Field(..., description="Notification message")
    severity: Literal["info", "success", "warning", "error", "critical"] = Field(
        default="info", description="Notification severity level"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp (ISO format)")
    dismissible: bool = Field(default=True, description="Whether notification can be dismissed")
    action_url: HttpUrl | None = Field(default=None, description="Optional action URL")
    action_label: str | None = Field(default=None, description="Label for action button")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content."""
        return "notification"


class NotificationResponse(ChatResponse[NotificationContent]):
    """Notification response for streaming to clients."""


# ============================================================================
# Form Response
# ============================================================================
class FormFieldDefinition(BaseModel):
    """Definition of a single form field."""

    name: str = Field(..., description="Field name (used as key in submission)")
    label: str = Field(..., description="Display label")
    field_type: Literal["text", "email", "number", "tel", "url", "textarea", "select", "checkbox", "radio"] = Field(
        ..., description="Field type"
    )
    required: bool = Field(default=True, description="Whether field is required")
    placeholder: str | None = Field(default=None, description="Placeholder text")
    options: list[str] | None = Field(default=None, description="Options for select/radio fields")
    default_value: str | None = Field(default=None, description="Default value")
    help_text: str | None = Field(default=None, description="Help text shown below field")


class InteractiveFormContent(ResponseContent):
    """Interactive form that can be filled out by users.

    Use this to collect structured input from users within the chat.
    """

    form_id: str = Field(..., description="Unique form identifier")
    title: str = Field(..., description="Form title")
    description: str | None = Field(default=None, description="Form description")
    fields: list[FormFieldDefinition] = Field(..., min_length=1, description="Form fields")
    submit_label: str = Field(default="Submit", description="Submit button label")
    submit_url: str | None = Field(default=None, description="URL to submit form data")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content."""
        return "interactive_form"


class InteractiveFormResponse(ChatResponse[InteractiveFormContent]):
    """Interactive form response for streaming to clients."""


# ============================================================================
# Location/Map Response
# ============================================================================
class LocationContent(ResponseContent):
    """Geographic location data for map display.

    Use this to show locations on a map in the chat UI.
    """

    name: str = Field(..., description="Location name")
    address: str = Field(..., description="Full address")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    description: str | None = Field(default=None, description="Location description")
    category: str | None = Field(default=None, description="Location category (e.g., restaurant, hotel)")
    rating: float | None = Field(default=None, ge=0, le=5, description="Location rating (0-5)")
    website: HttpUrl | None = Field(default=None, description="Location website")
    phone: str | None = Field(default=None, description="Contact phone number")

    def get_type(self) -> str:  # noqa: PLR6301
        """Return the type identifier for this content."""
        return "location"


class LocationResponse(ChatResponse[LocationContent]):
    """Location response for streaming to clients."""


# ============================================================================
# Chat Interface Implementation
# ============================================================================
class CustomResponseChat(ChatInterface):
    """Example chat interface demonstrating custom response types.

    This chat responds to specific keywords with custom response types:
    - "analytics" or "dashboard" -> Analytics data
    - "product" or "shop" -> Product catalog
    - "alert" or "notify" -> System notification
    - "form" or "survey" -> Interactive form
    - "location" or "map" -> Location data
    - Everything else -> Normal LLM conversation
    """

    def __init__(self) -> None:
        """Initialize the chat with an LLM."""
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle incoming chat messages and return appropriate responses."""
        message_lower = message.lower()

        # Analytics dashboard
        if "analytics" in message_lower or "dashboard" in message_lower:
            yield self.create_text_response("📊 Here's your analytics dashboard:")

            analytics = AnalyticsSummaryContent(
                total_visitors=45230,
                page_views=128450,
                bounce_rate=0.42,
                avg_session_duration=245.5,
                conversion_rate=0.034,
                revenue=89234.50,
                currency="USD",
            )
            yield AnalyticsSummaryResponse(content=analytics)

            yield self.create_text_response(
                "\nKey insights:\n"
                "- Conversion rate is up 12% from last month\n"
                "- Average session duration increased by 30 seconds\n"
                "- Mobile traffic accounts for 68% of visitors"
            )

        # Product catalog
        elif "product" in message_lower or "shop" in message_lower:
            yield self.create_text_response("🛍️ Here are some featured products:")

            products = [
                ProductContent(
                    id="PROD001",
                    name="Premium Wireless Headphones",
                    description="High-quality wireless headphones with active noise cancellation",
                    price=299.99,
                    currency="USD",
                    image_url="https://example.com/images/headphones.jpg",
                    category="Electronics",
                    in_stock=True,
                    rating=4.7,
                    tags=["audio", "wireless", "premium"],
                ),
                ProductContent(
                    id="PROD002",
                    name="Ergonomic Office Chair",
                    description="Comfortable office chair with lumbar support and adjustable height",
                    price=449.99,
                    currency="USD",
                    image_url="https://example.com/images/chair.jpg",
                    category="Furniture",
                    in_stock=True,
                    rating=4.5,
                    tags=["furniture", "office", "ergonomic"],
                ),
                ProductContent(
                    id="PROD003",
                    name="Smart Watch Pro",
                    description="Advanced fitness tracking with heart rate monitoring and GPS",
                    price=399.99,
                    currency="USD",
                    image_url="https://example.com/images/watch.jpg",
                    category="Electronics",
                    in_stock=False,
                    rating=4.8,
                    tags=["wearable", "fitness", "smart"],
                ),
            ]

            for product in products:
                yield ProductResponse(content=product)

        # System notification
        elif "alert" in message_lower or "notify" in message_lower:
            yield self.create_text_response("🔔 System Notifications:")

            notifications = [
                NotificationContent(
                    title="Database Backup Complete",
                    message="All databases have been successfully backed up.",
                    severity="success",
                    dismissible=True,
                ),
                NotificationContent(
                    title="High Memory Usage",
                    message="Server memory usage is at 85%. Consider scaling up resources.",
                    severity="warning",
                    dismissible=True,
                    action_url="https://example.com/admin/resources",
                    action_label="View Resources",
                ),
                NotificationContent(
                    title="Security Update Required",
                    message="Critical security update available. Please update within 24 hours.",
                    severity="critical",
                    dismissible=False,
                    action_url="https://example.com/updates",
                    action_label="Update Now",
                ),
            ]

            for notification in notifications:
                yield NotificationResponse(content=notification)

        # Interactive form
        elif "form" in message_lower or "survey" in message_lower:
            yield self.create_text_response("📝 Please fill out this feedback form:")

            form = InteractiveFormContent(
                form_id="feedback_2025_001",
                title="Customer Feedback Survey",
                description="We value your feedback! Please take a moment to share your thoughts.",
                fields=[
                    FormFieldDefinition(
                        name="satisfaction",
                        label="How satisfied are you with our service?",
                        field_type="select",
                        options=["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied"],
                        required=True,
                    ),
                    FormFieldDefinition(
                        name="features",
                        label="Which features do you use most?",
                        field_type="checkbox",
                        options=["Analytics", "Reports", "Integrations", "API", "Mobile App"],
                        required=False,
                    ),
                    FormFieldDefinition(
                        name="improvement",
                        label="What can we improve?",
                        field_type="textarea",
                        placeholder="Share your suggestions...",
                        required=False,
                        help_text="Your feedback helps us build a better product",
                    ),
                    FormFieldDefinition(
                        name="email",
                        label="Email (optional)",
                        field_type="email",
                        placeholder="your@email.com",
                        required=False,
                        help_text="We'll only contact you about your feedback",
                    ),
                ],
                submit_label="Submit Feedback",
                submit_url="/api/feedback/submit",
            )
            yield InteractiveFormResponse(content=form)

        # Location data
        elif "location" in message_lower or "map" in message_lower or "place" in message_lower:
            yield self.create_text_response("📍 Here are some nearby locations:")

            locations = [
                LocationContent(
                    name="The Coffee Lab",
                    address="123 Main Street, San Francisco, CA 94102",
                    latitude=37.7749,
                    longitude=-122.4194,
                    description="Artisanal coffee shop with excellent espresso and pastries",
                    category="cafe",
                    rating=4.6,
                    website="https://example.com/coffee-lab",
                    phone="+1-415-555-0123",
                ),
                LocationContent(
                    name="Tech Hub Co-working",
                    address="456 Market Street, San Francisco, CA 94105",
                    latitude=37.7899,
                    longitude=-122.3997,
                    description="Modern co-working space with high-speed internet and meeting rooms",
                    category="co-working",
                    rating=4.8,
                    website="https://example.com/tech-hub",
                    phone="+1-415-555-0456",
                ),
            ]

            for location in locations:
                yield LocationResponse(content=location)

        # Default: use LLM for general conversation
        else:
            yield self.create_text_response(
                "I can show you different types of custom responses. Try asking about:\n"
                "- Analytics or dashboard\n"
                "- Products or shopping\n"
                "- Alerts or notifications\n"
                "- Forms or surveys\n"
                "- Locations or maps\n\n"
                "Or just chat with me normally!\n\n"
            )

            # Also generate a normal LLM response
            async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
                yield self.create_text_response(chunk)


if __name__ == "__main__":
    print("Custom Response Example Chat")
    print("=" * 50)
    print()
    print("This example demonstrates custom response types in Ragbits.")
    print()
    print("To run this example:")
    print("  ragbits api run custom_responses_example:CustomResponseChat")
    print()
    print("Then open your browser to: http://127.0.0.1:8000")
    print()
    print("Try these commands in the chat:")
    print("  - 'show me analytics'")
    print("  - 'show me products'")
    print("  - 'show me alerts'")
    print("  - 'show me a form'")
    print("  - 'show me locations'")
    print()
