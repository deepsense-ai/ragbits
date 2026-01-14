from abc import ABC, abstractmethod
from types import ModuleType
from typing import ClassVar

from pydantic import BaseModel

from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent

from .types import OAuth2Credentials, User, UserCredentials


class AuthOptions(Options):
    """Options for authentication backends."""

    pass


class AuthenticationResponse(BaseModel):
    """Result of an authentication attempt."""

    success: bool
    user: User | None = None
    session_id: str | None = None
    error_message: str | None = None


class AuthenticationBackend(ConfigurableComponent[AuthOptions], ABC):
    """Base class for authentication backends."""

    configuration_key: ClassVar[str] = "auth_backend"
    options_cls = AuthOptions
    default_module: ClassVar[ModuleType | None] = None

    @abstractmethod
    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResponse:
        """
        Authenticate a user with username/password credentials.

        Args:
            credentials: The user credentials

        Returns:
            AuthenticationResult with user and session if successful
        """
        pass

    @abstractmethod
    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResponse:
        """
        Authenticate a user with OAuth2 credentials.

        Args:
            oauth_credentials: OAuth2 authentication data

        Returns:
            AuthenticationResult with user and session if successful
        """
        pass

    @abstractmethod
    async def validate_session(self, session_id: str) -> AuthenticationResponse:
        """
        Validate a session.

        Args:
            session_id: The session ID to validate

        Returns:
            AuthenticationResult with user if valid
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
