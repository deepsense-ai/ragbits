"""
Ragbits Chat Example: Authenticated Chat Interface

This example demonstrates how to use the `AuthenticatedChatInterface` to create a chat application
with user authentication. It showcases different response types while ensuring only authenticated
users can access the chat functionality.

To run the script using preferred components run:

    ```bash
    uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat
     --auth examples.chat.authenticated_chat:get_auth_backend
    ```

The preferred components approach allows the CLI to automatically use your configured authentication
backend while keeping the ChatInterface class focused on its core functionality.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///

import asyncio
from collections.abc import AsyncGenerator

from ragbits.chat.auth import ListAuthenticationBackend
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType, Message
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM


class MyAuthenticatedChat(ChatInterface):
    """An example implementation of ChatInterface with user-specific responses."""

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


# Factory functions for preferred components
def get_auth_backend() -> ListAuthenticationBackend:
    """Factory function to create the preferred authentication backend."""
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

    return ListAuthenticationBackend(users)
