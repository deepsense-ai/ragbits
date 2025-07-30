from abc import abstractmethod
from collections.abc import AsyncGenerator

from ragbits.core.prompt.base import ChatFormat

from ..interface._interface import ChatInterface
from ..interface.types import ChatContext, ChatResponse, ChatResponseType
from .base import AuthenticationBackend, AuthenticationResult


class AuthenticatedChatInterface(ChatInterface):
    """
    Base class for chat interfaces that require authentication.
    
    This extends ChatInterface to add authentication support using pluggable backends.
    """
    
    def __init__(self, auth_backend: AuthenticationBackend):
        """
        Initialize with an authentication backend.
        
        Args:
            auth_backend: The authentication backend to use
        """
        super().__init__()
        self.auth_backend = auth_backend
    
    async def setup(self) -> None:
        """Setup the chat interface and authentication backend."""
        await super().setup()
        await self.auth_backend.setup()
    
    async def chat(
        self,
        message: str,
        history: ChatFormat | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Process a chat message with authentication validation.
        
        Validates the session before processing the message.
        """
        if context is None:
            context = ChatContext()
        
        # Validate authentication if session_id is provided
        if context.session_id:
            auth_result = await self.auth_backend.validate_session(context.session_id)
            if not auth_result.success:
                yield ChatResponse(
                    type=ChatResponseType.TEXT, 
                    content=f"Authentication failed: {auth_result.error_message}"
                )
                return
            
            # Add user info to context
            if auth_result.user:
                context.state["authenticated_user"] = auth_result.user.model_dump()
        else:
            # No session provided - handle based on your requirements
            yield ChatResponse(
                type=ChatResponseType.TEXT,
                content="Authentication required. Please login first."
            )
            return
        
        # Proceed with authenticated chat
        async for response in self.authenticated_chat(message, history, context):
            yield response
    
    @abstractmethod
    async def authenticated_chat(
        self,
        message: str,
        history: ChatFormat | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Process a chat message for an authenticated user.
        
        This method is called after authentication validation passes.
        The user information is available in context.state["authenticated_user"].
        
        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Chat context with session_id and authenticated user info
            
        Yields:
            ChatResponse objects
        """
        pass
    
    async def authenticate_user(self, username: str, password: str) -> AuthenticationResult:
        """
        Authenticate a user with username/password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            AuthenticationResult with session info if successful
        """
        from .models import UserCredentials
        
        credentials = UserCredentials(username=username, password=password)
        return await self.auth_backend.authenticate_with_credentials(credentials)
    
    async def authenticate_oauth2(self, access_token: str, token_type: str = "bearer") -> AuthenticationResult:
        """
        Authenticate a user with OAuth2 token.
        
        Args:
            access_token: OAuth2 access token
            token_type: Token type (default: bearer)
            
        Returns:
            AuthenticationResult with session info if successful
        """
        from .models import OAuth2Credentials
        
        oauth_creds = OAuth2Credentials(access_token=access_token, token_type=token_type) 
        return await self.auth_backend.authenticate_with_oauth2(oauth_creds)
    
    async def logout_user(self, session_id: str) -> bool:
        """
        Logout a user by revoking their session.
        
        Args:
            session_id: Session ID to revoke
            
        Returns:
            True if successfully logged out
        """
        return await self.auth_backend.revoke_session(session_id)