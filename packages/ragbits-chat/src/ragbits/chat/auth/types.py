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


class JWTToken(BaseModel):
    """Represents a JWT authentication jwt_token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration
    refresh_token: str | None = None
    user: User


LoginRequest = UserCredentials


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


class OAuth2AuthorizeResponse(BaseModel):
    """
    Response for OAuth2 authorization URL request
    """

    authorize_url: str = Field(..., description="URL to redirect user to for OAuth2 authorization")
    state: str = Field(..., description="State parameter for CSRF protection")
