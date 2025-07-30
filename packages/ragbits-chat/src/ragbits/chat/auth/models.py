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


class UserSession(BaseModel):
    """Represents an active user session."""

    session_id: str
    user: User
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
