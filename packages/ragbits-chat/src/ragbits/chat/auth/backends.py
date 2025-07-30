import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from ragbits.chat.auth.base import AuthenticationBackend, AuthenticationResult
from ragbits.chat.auth.models import OAuth2Credentials, User, UserCredentials, UserSession


class ListAuthBackend(AuthenticationBackend):
    """Authentication backend using a predefined list of users."""

    def __init__(self, users: list[dict[str, Any]]):
        """
        Initialize with a list of user dictionaries.

        Args:
            users: List of user dicts with 'username', 'password', and optional fields
        """
        self.users = {}
        self.sessions = {}

        for user_data in users:
            # Hash passwords for security
            password_hash = hashlib.sha256(user_data["password"].encode()).hexdigest()
            self.users[user_data["username"]] = {
                "password_hash": password_hash,
                "user": User(
                    user_id=user_data.get("user_id", str(uuid.uuid4())),
                    username=user_data["username"],
                    email=user_data.get("email"),
                    full_name=user_data.get("full_name"),
                    roles=user_data.get("roles", []),
                    metadata=user_data.get("metadata", {}),
                ),
            }

    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResult:
        user_data = self.users.get(credentials.username)
        if not user_data:
            return AuthenticationResult(success=False, error_message="User not found")

        password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
        if password_hash != user_data["password_hash"]:
            return AuthenticationResult(success=False, error_message="Invalid password")

        # Create session
        session_id = str(uuid.uuid4())
        session = UserSession(
            session_id=session_id,
            user=user_data["user"],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),
        )
        self.sessions[session_id] = session

        return AuthenticationResult(success=True, user=user_data["user"], session=session)

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResult:
        return AuthenticationResult(success=False, error_message="OAuth2 not supported by ListAuthBackend")

    async def validate_session(self, session_id: str) -> AuthenticationResult:
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return AuthenticationResult(success=False, error_message="Invalid session")

        if session.expires_at and datetime.now() > session.expires_at:
            session.is_active = False
            return AuthenticationResult(success=False, error_message="Session expired")

        return AuthenticationResult(success=True, user=session.user, session=session)

    async def revoke_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            return True
        return False


class DatabaseAuthBackend(AuthenticationBackend):
    """Authentication backend using database storage."""

    def __init__(self, db_connection_string: str):
        """
        Initialize with database connection.

        Args:
            db_connection_string: Database connection string
        """
        self.db_connection_string = db_connection_string
        # In real implementation, initialize database connection
        # self.db = create_database_connection(db_connection_string)

    async def setup(self) -> None:
        """Setup database tables if needed."""
        # In real implementation:
        # await self.db.create_tables_if_not_exists()
        pass

    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResult:
        # In real implementation:
        # user = await self.db.get_user_by_username(credentials.username)
        # if user and verify_password(credentials.password, user.password_hash):
        #     session = await self.db.create_session(user)
        #     return AuthenticationResult(success=True, user=user, session=session)
        return AuthenticationResult(success=False, error_message="Database authentication not implemented")

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResult:
        # In real implementation:
        # user_info = await self.verify_oauth_token(oauth_credentials.access_token)
        # user = await self.db.get_or_create_user_from_oauth(user_info)
        # session = await self.db.create_session(user)
        return AuthenticationResult(success=False, error_message="OAuth2 database authentication not implemented")

    async def validate_session(self, session_id: str) -> AuthenticationResult:
        # In real implementation:
        # session = await self.db.get_active_session(session_id)
        # if session and not session.is_expired():
        #     return AuthenticationResult(success=True, user=session.user, session=session)
        return AuthenticationResult(success=False, error_message="Session validation not implemented")

    async def revoke_session(self, session_id: str) -> bool:
        # In real implementation:
        # return await self.db.deactivate_session(session_id)
        return False


class OAuth2Backend(AuthenticationBackend):
    """Authentication backend for OAuth2 providers (Google, GitHub, etc.)."""

    def __init__(self, provider: str, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize OAuth2 backend.

        Args:
            provider: OAuth2 provider name (google, github, etc.)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
        """
        self.provider = provider
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.sessions = {}

    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResult:
        return AuthenticationResult(success=False, error_message="Use OAuth2 flow for authentication")

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResult:
        # In real implementation, verify the OAuth2 token with the provider
        # user_info = await self.verify_token_with_provider(oauth_credentials.access_token)

        # For demo purposes, create a mock user
        user = User(
            user_id=str(uuid.uuid4()),
            username=f"oauth_user_{secrets.token_hex(4)}",
            email="user@example.com",
            full_name="OAuth User",
            roles=["user"],
            metadata={"provider": self.provider},
        )

        session_id = str(uuid.uuid4())
        session = UserSession(
            session_id=session_id, user=user, created_at=datetime.now(), expires_at=oauth_credentials.expires_at
        )
        self.sessions[session_id] = session

        return AuthenticationResult(success=True, user=user, session=session)

    async def validate_session(self, session_id: str) -> AuthenticationResult:
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return AuthenticationResult(success=False, error_message="Invalid session")

        if session.expires_at and datetime.now() > session.expires_at:
            session.is_active = False
            return AuthenticationResult(success=False, error_message="Session expired")

        return AuthenticationResult(success=True, user=session.user, session=session)

    async def revoke_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            return True
        return False
