from abc import ABC, abstractmethod

from pydantic import BaseModel

from .models import JWTToken, OAuth2Credentials, User, UserCredentials


class AuthenticationResult(BaseModel):
    """Result of an authentication attempt."""

    success: bool
    user: User | None = None
    jwt_token: JWTToken | None = None  # JWT jwt_token for new implementations
    error_message: str | None = None


class AuthenticationBackend(ABC):
    """Base class for authentication backends."""

    @abstractmethod
    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResult:
        """
        Authenticate a user with username/password credentials.

        Args:
            credentials: The user credentials

        Returns:
            AuthenticationResult with user and session if successful
        """
        pass

    @abstractmethod
    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResult:
        """
        Authenticate a user with OAuth2 credentials.

        Args:
            oauth_credentials: OAuth2 authentication data

        Returns:
            AuthenticationResult with user and session if successful
        """
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> AuthenticationResult:
        """
        Validate a JWT jwt_token.

        Args:
            token: The JWT jwt_token to validate

        Returns:
            AuthenticationResult with user if valid
        """
        # Default implementation for backward compatibility
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke/logout a session.

        Args:
            token: The jwt_token to revoke

        Returns:
            True if successfully revoked
        """
        pass
