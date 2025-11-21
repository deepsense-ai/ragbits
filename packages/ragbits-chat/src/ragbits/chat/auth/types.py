from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class User(BaseModel):
    """Represents an authenticated user."""

    user_id: str
    username: str
    email: str | None = None
    full_name: str | None = None
    roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserCredentials(BaseModel):
    """Represents user login credentials."""

    username: str
    password: str


class OAuth2Credentials(BaseModel):
    """Represents OAuth2 authentication data from Discord."""

    access_token: str
    token_type: str = "bearer"


LoginRequest = UserCredentials


class LoginResponse(BaseModel):
    """
    Response body for login with session-based authentication.

    The session ID is set as an HTTP-only cookie by the backend.
    Frontend only receives user information.
    """

    success: bool = Field(..., description="Whether login was successful")
    user: User | None = Field(None, description="User information")
    error_message: str | None = Field(None, description="Error message if login failed")


class OAuth2AuthorizeResponse(BaseModel):
    """
    Response for OAuth2 authorization URL request
    """

    authorize_url: str = Field(..., description="URL to redirect user to for OAuth2 authorization")
    state: str = Field(..., description="State parameter for CSRF protection")


class Session(BaseModel):
    """Represents a user session."""

    session_id: str
    user: User
    provider: str
    oauth_token: str  # Provider's OAuth token
    token_type: str
    created_at: datetime
    expires_at: datetime


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    async def create_session(self, session: Session) -> str:
        """
        Create a new session.

        Args:
            session: Session object to store

        Returns:
            Session ID
        """
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session object if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        pass
