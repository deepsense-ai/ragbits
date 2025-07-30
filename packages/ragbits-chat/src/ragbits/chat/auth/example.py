"""
Example implementation showing how to use the authentication system.
"""

from collections.abc import AsyncGenerator

from ragbits.core.prompt.base import ChatFormat

from ..interface.types import ChatContext, ChatResponse
from .authenticated_interface import AuthenticatedChatInterface
from .backends import ListAuthBackend


class ExampleAuthenticatedChat(AuthenticatedChatInterface):
    """Example authenticated chat implementation."""

    async def authenticated_chat(
        self,
        message: str,
        history: ChatFormat | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle chat for authenticated users."""
        if context and "authenticated_user" in context.state:
            user = context.state["authenticated_user"]
            yield self.create_text_response(f"Hello {user['username']}, you said: {message}")
        else:
            yield self.create_text_response("Authentication info not found.")


# Example usage:
async def example_usage():
    """Demonstrate how to use the authentication system."""

    # 1. Create users list for ListAuthBackend
    users = [
        {
            "username": "alice",
            "password": "secret123",
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "roles": ["user", "admin"],
        },
        {
            "username": "bob",
            "password": "password456",
            "email": "bob@example.com",
            "full_name": "Bob Johnson",
            "roles": ["user"],
        },
    ]

    # 2. Create authentication backend
    auth_backend = ListAuthBackend(users)

    # 3. Create authenticated chat interface
    chat = ExampleAuthenticatedChat(auth_backend)
    await chat.setup()

    # 4. Authenticate user
    auth_result = await chat.authenticate_user("alice", "secret123")

    if auth_result.success:
        print(f"Authentication successful for user: {auth_result.user.username}")

        # 5. Use the session in chat context
        context = ChatContext(session_id=auth_result.session.session_id)

        # 6. Chat with authentication
        async for response in chat.chat("Hello!", context=context):
            if text := response.as_text():
                print(f"Response: {text}")
    else:
        print(f"Authentication failed: {auth_result.error_message}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
