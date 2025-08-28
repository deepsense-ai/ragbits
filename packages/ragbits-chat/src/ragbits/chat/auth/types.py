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
    """Represents OAuth2 authentication data."""

    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scope: str | None = None


class JWTToken(BaseModel):
    """Represents a JWT authentication jwt_token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration
    refresh_token: str | None = None
    user: User


class CredentialsLoginRequest(BaseModel):
    """
    Request body for user login
    """

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


LoginRequest = CredentialsLoginRequest


class LoginResponse(BaseModel):
    """
    Response body for successful login
    """

    success: bool = Field(..., description="Whether login was successful")
    user: User | None = Field(None, description="User information")
    error_message: str | None = Field(None, description="Error message if login failed")
    jwt_token: JWTToken | None = Field(..., description="Access jwt_token")


class LogoutRequest(BaseModel):
    """
    Request body for user logout
    """

    token: str = Field(..., description="Session ID to logout")
