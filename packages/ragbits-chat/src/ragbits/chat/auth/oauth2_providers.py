"""OAuth2 provider implementations for various authentication services."""

from abc import ABC, abstractmethod
from typing import Any

from ragbits.chat.auth.types import User


class OAuth2Provider(ABC):
    """Abstract base class for OAuth2 providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'discord')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'Discord')."""
        pass

    @property
    @abstractmethod
    def authorize_url(self) -> str:
        """OAuth2 authorization endpoint."""
        pass

    @property
    @abstractmethod
    def token_url(self) -> str:
        """OAuth2 token exchange endpoint."""
        pass

    @property
    @abstractmethod
    def user_info_url(self) -> str:
        """User info endpoint."""
        pass

    @property
    @abstractmethod
    def scope(self) -> str:
        """OAuth2 scopes to request."""
        pass

    @abstractmethod
    def create_user_from_data(self, user_data: dict[str, Any]) -> User:
        """
        Create a User object from provider-specific user data.

        Args:
            user_data: Raw user data from the provider

        Returns:
            User object
        """
        pass


class DiscordOAuth2Provider(OAuth2Provider):
    """Discord OAuth2 provider implementation."""

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "discord"

    @property
    def display_name(self) -> str:
        """Return the human-readable provider name."""
        return "Discord"

    @property
    def authorize_url(self) -> str:
        """Return the OAuth2 authorization URL."""
        return "https://discord.com/api/oauth2/authorize"

    @property
    def token_url(self) -> str:
        """Return the OAuth2 token exchange URL."""
        return "https://discord.com/api/oauth2/token"

    @property
    def user_info_url(self) -> str:
        """Return the user info API URL."""
        return "https://discord.com/api/users/@me"

    @property
    def scope(self) -> str:
        """Return the OAuth2 scope to request."""
        return "identify email"

    def create_user_from_data(self, user_data: dict[str, Any]) -> User:  # noqa: PLR6301
        """Create User object from Discord data."""
        return User(
            user_id=f"discord_{user_data['id']}",
            username=user_data.get("username", ""),
            email=user_data.get("email"),
            full_name=user_data.get("global_name"),
            roles=["user"],
            metadata={
                "provider": "discord",
                "avatar": user_data.get("avatar"),
                "discriminator": user_data.get("discriminator"),
            },
        )
