r"""
Ragbits Chat Example: Authenticated Chat Interface

This example demonstrates how to use the `AuthenticatedChatInterface` to create a chat application
with user authentication. It showcases different response types while ensuring only authenticated
users can access the chat functionality.

## Running with Credentials Authentication (ListAuthenticationBackend)

To run with username/password authentication:

    ```bash
    uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat
     --auth examples.chat.authenticated_chat:get_auth_backend
    ```

Test users:
- Username: admin, Password: admin123
- Username: alice, Password: alice123

## Running with Discord OAuth2 Authentication

To run with Discord OAuth2 authentication:

    ```bash
    export DISCORD_CLIENT_ID="your_client_id_here"
    export DISCORD_CLIENT_SECRET="your_client_secret_here"
    uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat \\
     --auth examples.chat.authenticated_chat:get_discord_auth_backend
    ```

Prerequisites for Discord OAuth2:
1. Create a Discord application at https://discord.com/developers/applications
2. Add redirect URI: http://localhost:8000/api/auth/callback/discord
3. Set environment variables DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET

## Running with Google OAuth2 Authentication

To run with Google OAuth2 authentication:

    ```bash
    export GOOGLE_CLIENT_ID="your_client_id_here"
    export GOOGLE_CLIENT_SECRET="your_client_secret_here"
    uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat \\
     --auth examples.chat.authenticated_chat:get_google_auth_backend
    ```

Prerequisites for Google OAuth2:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: http://localhost:8000/api/auth/callback/google
4. Set environment variables GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

## Running with Multiple Authentication Methods

To run with both credentials and Discord OAuth2:

    ```bash
    export DISCORD_CLIENT_ID="your_client_id_here"
    export DISCORD_CLIENT_SECRET="your_client_secret_here"
    uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat \\
     --auth examples.chat.authenticated_chat:get_multi_auth_backend
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
from ragbits.chat.auth.backends import MultiAuthenticationBackend, OAuth2AuthenticationBackend
from ragbits.chat.auth.oauth2_providers import DiscordOAuth2Provider, GoogleOAuth2Provider
from ragbits.chat.auth.session_store import InMemorySessionStore
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt.base import ChatFormat


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
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Authenticated chat implementation that provides user-specific responses.

        This method is called after authentication validation passes.
        The user information is available in context.user.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Chat context with session_id and authenticated user info

        Yields:
            ChatResponse objects containing different types of content
        """
        # Get authenticated user info
        user_info = context.user

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
                "session_context": context.session_id if context.session_id else "unknown",
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
            "user_id": "8e6c5871-3817-4d62-828f-ef6789de31b9",
            "username": "admin",
            "password": "admin123",
            "email": "admin@example.com",
            "full_name": "System Administrator",
            "roles": ["admin", "moderator", "user"],
            "metadata": {"department": "IT", "clearance_level": "high"},
        },
        {
            "user_id": "d3afde97-35fb-41d0-9aa6-6a1c822db63e",
            "username": "moderator",
            "password": "mod123",
            "email": "mod@example.com",
            "full_name": "Community Moderator",
            "roles": ["moderator", "user"],
            "metadata": {"department": "Community", "shift": "day"},
        },
        {
            "user_id": "7ef3d9d5-cdad-405a-a919-3d3ee5e1c34d",
            "username": "alice",
            "password": "alice123",
            "email": "alice@example.com",
            "full_name": "Alice Johnson",
            "roles": ["user"],
            "metadata": {"department": "Marketing", "join_date": "2024-01-15"},
        },
        {
            "user_id": "acac16db-37f0-43cb-b18f-b005c3c3de88",
            "username": "bob",
            "password": "bob123",
            "email": "bob@example.com",
            "full_name": "Bob Smith",
            "roles": ["user"],
            "metadata": {"department": "Sales", "territory": "North America"},
        },
    ]

    return ListAuthenticationBackend(
        users=users,
        session_store=InMemorySessionStore(),
    )


def get_discord_auth_backend() -> OAuth2AuthenticationBackend:
    """
    Factory function to create Discord OAuth2 authentication backend.

    This backend uses Discord OAuth2 for authentication. Users sign in with their Discord account.

    Prerequisites:
    1. Create a Discord application at https://discord.com/developers/applications
    2. Set redirect URI to: http://localhost:8000/api/auth/callback/discord
    3. Set environment variables:
       - DISCORD_CLIENT_ID: Your Discord application client ID
       - DISCORD_CLIENT_SECRET: Your Discord application client secret

    OAuth2 Flow:
    1. User clicks "Sign in with Discord" button
    2. User is redirected to Discord to authorize
    3. Discord redirects back to /api/auth/callback/discord with authorization code
    4. Backend exchanges code for access token
    5. Backend fetches user info from Discord API
    6. Backend creates session and authenticates user

    Note: The redirect_uri is automatically set to the provider-specific endpoint.
    If you need a custom redirect_uri, you can pass it explicitly or set OAUTH2_REDIRECT_URI env var.
    """
    # Credentials and redirect_uri are automatically read from environment variables:
    # DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, and optionally OAUTH2_REDIRECT_URI
    # If not set, redirect_uri defaults to http://localhost:8000/api/auth/callback/discord
    return OAuth2AuthenticationBackend(
        session_store=InMemorySessionStore(),
        provider=DiscordOAuth2Provider(),
    )


def get_google_auth_backend() -> OAuth2AuthenticationBackend:
    """
    Factory function to create Google OAuth2 authentication backend.

    This backend uses Google OAuth2 for authentication. Users sign in with their Google account.

    Prerequisites:
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Create OAuth 2.0 Client ID (Web application)
    3. Add authorized redirect URI: http://localhost:8000/api/auth/callback/google
    4. Set environment variables:
       - GOOGLE_CLIENT_ID: Your Google OAuth2 client ID
       - GOOGLE_CLIENT_SECRET: Your Google OAuth2 client secret

    OAuth2 Flow:
    1. User clicks "Sign in with Google" button
    2. User is redirected to Google to authorize
    3. Google redirects back to /api/auth/callback/google with authorization code
    4. Backend exchanges code for access token
    5. Backend fetches user info from Google API
    6. Backend creates session and authenticates user

    Note: The redirect_uri is automatically set to the provider-specific endpoint.
    If you need a custom redirect_uri, you can pass it explicitly or set OAUTH2_REDIRECT_URI env var.
    """
    # Credentials and redirect_uri are automatically read from environment variables:
    # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and optionally OAUTH2_REDIRECT_URI
    # If not set, redirect_uri defaults to http://localhost:8000/api/auth/callback/google
    return OAuth2AuthenticationBackend(
        session_store=InMemorySessionStore(),
        provider=GoogleOAuth2Provider(),
    )


def get_multi_auth_backend() -> MultiAuthenticationBackend:
    """
    Factory function to create a multi-authentication backend.

    This backend supports both credentials-based authentication and Discord OAuth2,
    allowing users to choose their preferred login method.

    The frontend will automatically show both login options based on the backend configuration.
    """
    return MultiAuthenticationBackend(
        backends=[
            get_auth_backend(),  # Credentials-based authentication
            get_discord_auth_backend(),  # Discord OAuth2 authentication
        ]
    )
