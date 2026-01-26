"""OAuth2 provider implementations for various authentication services."""

from collections.abc import Callable

from pydantic.config import JsonDict

from ragbits.chat.auth.types import User


class OAuth2Provider:
    """Abstract base class for OAuth2 providers."""

    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        authorize_url: str,
        token_url: str,
        user_info_url: str,
        scopes: list[str],
        user_factory: Callable[[JsonDict], User],
    ) -> None:
        self._name = name
        self._display_name = display_name
        self._authorize_url = authorize_url
        self._token_url = token_url
        self._user_info_url = user_info_url
        self._scopes = scopes
        self._user_factory = user_factory

    @property
    def name(self) -> str:
        """Provider name (e.g., 'discord')."""
        return self._name

    @property
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'Discord')."""
        return self._display_name

    @property
    def authorize_url(self) -> str:
        """OAuth2 authorization endpoint."""
        return self._authorize_url

    @property
    def token_url(self) -> str:
        """OAuth2 token exchange endpoint."""
        return self._token_url

    @property
    def user_info_url(self) -> str:
        """User info endpoint."""
        return self._user_info_url

    @property
    def scope(self) -> str:
        """OAuth2 scopes to request."""
        return " ".join(self._scopes)

    def create_user_from_data(self, user_data: JsonDict) -> User:
        """
        Create a User object from provider-specific user data.

        Args:
            user_data: Raw user data from the provider

        Returns:
            User object
        """
        return self._user_factory(user_data)


class OAuth2Providers:
    """Namespace for built-in OAuth2 provider configurations."""

    DISCORD = OAuth2Provider(
        name="discord",
        display_name="Discord",
        authorize_url="https://discord.com/api/oauth2/authorize",
        token_url="https://discord.com/api/oauth2/token",  # noqa: S106
        user_info_url="https://discord.com/api/users/@me",
        scopes=["identify", "email"],
        user_factory=lambda user_data: User(
            user_id=f"discord_{user_data['id']}",
            username=str(user_data.get("username", "")),
            email=str(user_data["email"]) if user_data.get("email") else None,
            full_name=str(user_data["global_name"]) if user_data.get("global_name") else None,
            roles=["user"],
            metadata={
                "provider": "discord",
                "avatar": user_data.get("avatar"),
                "discriminator": user_data.get("discriminator"),
            },
        ),
    )

    GOOGLE = OAuth2Provider(
        name="google",
        display_name="Google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",  # noqa: S106
        user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
        scopes=["openid", "email", "profile"],
        user_factory=lambda user_data: User(
            user_id=f"google_{user_data['id']}",
            username=str(user_data.get("email", "")).split("@")[0],
            email=str(user_data["email"]) if user_data.get("email") else None,
            full_name=str(user_data["name"]) if user_data.get("name") else None,
            roles=["user"],
            metadata={
                "provider": "google",
                "picture": user_data.get("picture"),
                "verified_email": user_data.get("verified_email"),
                "hd": user_data.get("hd"),  # Google Workspace domain
            },
        ),
    )
