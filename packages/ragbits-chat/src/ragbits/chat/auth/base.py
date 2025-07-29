from abc import ABC, abstractmethod

from pydantic import BaseModel

from .models import OAuth2Credentials, User, UserCredentials, UserSession


class AuthenticationResult(BaseModel):
    """Result of an authentication attempt."""
    success: bool
    user: User | None = None
    session: UserSession | None = None
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
    async def validate_session(self, session_id: str) -> AuthenticationResult:
        """
        Validate an existing session.

        Args:
            session_id: The session ID to validate

        Returns:
            AuthenticationResult with user and session if valid
        """
        pass

    @abstractmethod
    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke/logout a session.

        Args:
            session_id: The session ID to revoke

        Returns:
            True if successfully revoked
        """
        pass

    async def setup(self) -> None:
        """
        Setup the authentication backend.
        Called during initialization, can be overridden for setup logic.
        """
        pass