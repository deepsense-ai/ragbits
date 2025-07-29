"""
Example showing how to use RagbitsAPI with authentication.
"""

from collections.abc import AsyncGenerator

from ragbits.core.prompt.base import ChatFormat

from ..api import RagbitsAPI
from ..interface.types import ChatContext, ChatResponse
from .authenticated_interface import AuthenticatedChatInterface
from .backends import ListAuthBackend


class ExampleAuthenticatedChatAPI(AuthenticatedChatInterface):
    """Example authenticated chat for API usage."""
    
    async def authenticated_chat(
        self,
        message: str,
        history: ChatFormat | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle chat for authenticated users."""
        if context and "authenticated_user" in context.state:
            user = context.state["authenticated_user"]
            yield self.create_text_response(f"Hello {user['username']}! You said: {message}")
            yield self.create_text_response(f"Your user ID is: {user['user_id']}")
            if user.get("roles"):
                yield self.create_text_response(f"Your roles: {', '.join(user['roles'])}")
        else:
            yield self.create_text_response("Authentication info not found.")


def create_authenticated_api():
    """Create an authenticated RagbitsAPI instance."""
    
    # Define users for ListAuthBackend
    users = [
        {
            "username": "admin",
            "password": "admin123",
            "email": "admin@example.com",
            "full_name": "Administrator",
            "roles": ["admin", "user"]
        },
        {
            "username": "john",
            "password": "password123",
            "email": "john@example.com", 
            "full_name": "John Doe",
            "roles": ["user"]
        },
        {
            "username": "jane",
            "password": "secret456",
            "email": "jane@example.com",
            "full_name": "Jane Smith", 
            "roles": ["user", "moderator"]
        }
    ]
    
    # Create authentication backend
    auth_backend = ListAuthBackend(users)
    
    # Create authenticated chat interface
    chat_interface = ExampleAuthenticatedChatAPI(auth_backend)
    
    # Create RagbitsAPI with authentication
    api = RagbitsAPI(
        chat_interface=type(chat_interface),
        auth_backend=auth_backend,
        cors_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        debug_mode=True
    )
    
    return api


def main():
    """Run the authenticated API server."""
    api = create_authenticated_api()
    
    print("🚀 Starting RagbitsAPI with authentication...")
    print("📝 Available users:")
    print("   - admin / admin123 (admin, user)")
    print("   - john / password123 (user)")
    print("   - jane / secret456 (user, moderator)")
    print()
    print("🔐 Authentication workflow:")
    print("   1. POST /api/auth/login with username/password")
    print("   2. Use session_id from response as Bearer token") 
    print("   3. Include 'Authorization: Bearer <session_id>' in chat requests")
    print("   4. POST /api/auth/logout to logout")
    print()
    print("📡 Server running at: http://127.0.0.1:8000")
    
    api.run(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()