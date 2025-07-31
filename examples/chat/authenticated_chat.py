"""
Ragbits Chat Example: Authenticated Chat Interface

This example demonstrates how to use the `AuthenticatedChatInterface` to create a chat application
with user authentication. It showcases different response types while ensuring only authenticated
users can access the chat functionality.

To run the script, execute the following command:

    ```bash
    uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat
    ```

Or run directly with full authentication support:

    ```bash
    python examples/chat/authenticated_chat.py
    ```

Note: The CLI version has limited authentication support. Use the direct Python execution for full features.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ragbits.chat.api import RagbitsAPI
from ragbits.chat.auth import ListAuthBackend
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType, Message
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM


class LikeFormExample(BaseModel):
    """A simple example implementation of the like form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(
        title="Like Form",
        json_schema_serialization_defaults_required=True,
    )

    like_reason: str = Field(
        description="Why do you like this?",
        min_length=1,
    )


class DislikeFormExample(BaseModel):
    """A simple example implementation of the dislike form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(title="Dislike Form", json_schema_serialization_defaults_required=True)

    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(
        description="What was the issue?"
    )
    feedback: str = Field(description="Please provide more details", min_length=1)


class UserSettingsFormExample(BaseModel):
    """A simple example implementation of the chat form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(title="Chat Form", json_schema_serialization_defaults_required=True)

    language: Literal["English", "Polish"] = Field(description="Please select the language", default="English")


class MyAuthenticatedChat(ChatInterface):
    """An example implementation of ChatInterface with user-specific responses."""

    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )
    user_settings = UserSettings(form=UserSettingsFormExample)

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="🔐 Authenticated Ragbits Chat", subtitle="by deepsense.ai - Secure Chat Experience", logo="🛡️"
        ),
        welcome_message=(
            "🔐 **Welcome to Authenticated Ragbits Chat!**\n\n"
            "This is a secure chat environment where you need to authenticate to access the AI assistant.\n\n"
            "**Features:**\n"
            "- 🛡️ User authentication with role-based access\n"
            "- 👤 Personalized responses based on your profile\n"
            "- 📊 User-specific chat history and context\n"
            "- 🔒 Secure session management\n\n"
            "Please log in to start chatting!"
        ),
    )

    conversation_history = True

    def __init__(self):
        super().__init__()
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Authenticated chat implementation that provides user-specific responses.

        This method is called after authentication validation passes.
        The user information is available in context.state["authenticated_user"].

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Chat context with session_id and authenticated user info

        Yields:
            ChatResponse objects containing different types of content
        """
        # Get authenticated user info
        user_info = context.state.get("authenticated_user") if context else None

        if not user_info:
            yield self.create_text_response("⚠️ Authentication information not found.")
            return

        username = user_info.username
        full_name = user_info.full_name
        user_roles = user_info.roles
        user_id = user_info.user_id

        # Create user-specific reference
        yield self.create_reference(
            title=f"User Profile: {full_name}",
            content=f"Authenticated user: {username} (ID: {user_id[:8]}...) with roles: {', '.join(user_roles)}",
            url=f"https://example.com/users/{user_id}",
        )

        # Create user-specific state update
        yield self.create_state_update(
            {
                "authenticated_user_id": user_id,
                "session_context": context.session_id if context and context.session_id else "unknown",
                "user_roles": user_roles,
                "chat_timestamp": asyncio.get_event_loop().time(),
            }
        )

        # Show a personalized image based on user role
        if "admin" in user_roles:
            yield self.create_image_response(
                str(uuid.uuid4()),
                "https://media.istockphoto.com/id/1300845620/photo/user-icon-human-person-symbol-social-profile-icon-avatar-login-sign-web-user-symbol.jpg",
            )

        # Role-specific live updates
        role_updates = []
        if "admin" in user_roles:
            role_updates.extend(
                [
                    self.create_live_update("admin_0", LiveUpdateType.START, "🔧 [ADMIN] Accessing admin resources..."),
                    self.create_live_update(
                        "admin_0",
                        LiveUpdateType.FINISH,
                        "🔧 [ADMIN] Admin resources loaded",
                        "Full system access granted.",
                    ),
                ]
            )

        if "moderator" in user_roles:
            role_updates.extend(
                [
                    self.create_live_update(
                        "mod_1", LiveUpdateType.START, "🛡️ [MODERATOR] Checking content policies..."
                    ),
                    self.create_live_update(
                        "mod_1",
                        LiveUpdateType.FINISH,
                        "🛡️ [MODERATOR] Content policy check complete",
                        "All content meets guidelines.",
                    ),
                ]
            )

        # Standard user updates
        role_updates.extend(
            [
                self.create_live_update(
                    "user_2", LiveUpdateType.START, f"🤖 [CHAT] Processing message for {username}..."
                ),
                self.create_live_update(
                    "user_2",
                    LiveUpdateType.FINISH,
                    "🤖 [CHAT] Message processed",
                    f"Generating personalized response for {full_name}.",
                ),
            ]
        )

        for live_update in role_updates:
            yield live_update
            await asyncio.sleep(1)

        # Create personalized system message
        system_message = (
            f"You are chatting with {full_name} (username: {username}). "
            f"Their roles are: {', '.join(user_roles)}. "
            f"Personalize your response based on their profile. "
            f"Be friendly and acknowledge their specific role if relevant."
        )

        # Prepare messages for LLM
        messages = [{"role": "system", "content": system_message}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        # Generate personalized response
        async for chunk in self.llm.generate_streaming(messages):
            yield self.create_text_response(chunk)

        # Role-specific followup suggestions
        followup_messages = [
            "Tell me about my user profile",
            f"What can I do as a {user_roles[0] if user_roles else 'user'}?",
        ]

        if "admin" in user_roles:
            followup_messages.extend(["Show admin dashboard", "Manage user permissions"])
        elif "moderator" in user_roles:
            followup_messages.extend(["Review flagged content", "Check community guidelines"])
        else:
            followup_messages.extend(["How do I get more permissions?", "What features are available to me?"])

        yield self.create_followup_messages(followup_messages[:4])  # Limit to 4 suggestions


def create_auth_backend() -> ListAuthBackend:
    """Create and return the authentication backend with example users."""
    users = [
        {
            "username": "admin",
            "password": "admin123",
            "email": "admin@example.com",
            "full_name": "System Administrator",
            "roles": ["admin", "moderator", "user"],
            "metadata": {"department": "IT", "clearance_level": "high"},
        },
        {
            "username": "moderator",
            "password": "mod123",
            "email": "mod@example.com",
            "full_name": "Community Moderator",
            "roles": ["moderator", "user"],
            "metadata": {"department": "Community", "shift": "day"},
        },
        {
            "username": "alice",
            "password": "alice123",
            "email": "alice@example.com",
            "full_name": "Alice Johnson",
            "roles": ["user"],
            "metadata": {"department": "Marketing", "join_date": "2024-01-15"},
        },
        {
            "username": "bob",
            "password": "bob123",
            "email": "bob@example.com",
            "full_name": "Bob Smith",
            "roles": ["user"],
            "metadata": {"department": "Sales", "territory": "North America"},
        },
    ]

    return ListAuthBackend(users)


def create_api() -> RagbitsAPI:
    """Create and configure the authenticated API."""
    auth_backend = create_auth_backend()
    chat_interface = MyAuthenticatedChat()

    api = RagbitsAPI(
        chat_interface=type(chat_interface),
        auth_backend=auth_backend,
        cors_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        debug_mode=True,
    )

    return api


def main() -> None:
    """Run the authenticated chat API server."""
    api = create_api()

    print("🔐 Starting Authenticated Ragbits Chat API...")
    print("=" * 50)
    print("👥 Available Users:")
    print("   🔧 admin / admin123      (admin, moderator, user)")
    print("   🛡️ moderator / mod123    (moderator, user)")
    print("   👤 alice / alice123      (user)")
    print("   👤 bob / bob123          (user)")
    print()
    print("🌐 API Endpoints:")
    print("   📝 POST /api/auth/login  - User authentication")
    print("   🚪 POST /api/auth/logout - User logout")
    print("   💬 POST /api/chat        - Chat (requires auth)")
    print("   👍 POST /api/feedback    - Feedback (requires auth)")
    print("   ⚙️  GET  /api/config     - Configuration")
    print()
    print("🔗 Web Interface: http://127.0.0.1:8000")
    print("📖 Test the authentication workflow using the web UI!")
    print("=" * 50)

    api.run(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
