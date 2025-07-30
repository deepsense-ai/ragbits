import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from ragbits.chat.auth.base import AuthenticationBackend, AuthenticationResult
from ragbits.chat.auth.models import JWTToken, OAuth2Credentials, User, UserCredentials


class ListAuthBackend(AuthenticationBackend):
    """Authentication backend using a predefined list of users."""

    def __init__(self, users: list[dict[str, Any]], jwt_secret: str = None):
        """
        Initialize with a list of user dictionaries.

        Args:
            users: List of user dicts with 'username', 'password', and optional fields
            jwt_secret: Secret key for JWT jwt_token signing (generates random if not provided)
        """
        self.users = {}
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.jwt_algorithm = "HS256"
        self.token_expiry_minutes = 30
        self.revoked_tokens = set()  # Blacklist for revoked tokens

        for user_data in users:
            # Hash passwords with bcrypt for security
            password_hash = bcrypt.hashpw(user_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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

        # Verify password with bcrypt
        if not bcrypt.checkpw(credentials.password.encode('utf-8'), user_data["password_hash"].encode('utf-8')):
            return AuthenticationResult(success=False, error_message="Invalid password")

        user = user_data["user"]

        # Create JWT jwt_token
        jwt_token = self._create_jwt_token(user)

        return AuthenticationResult(success=True, user=user, jwt_token=jwt_token)

    def _create_jwt_token(self, user: User) -> JWTToken:
        """Create a JWT jwt_token for the user."""
        now = datetime.now(timezone.utc)
        expires_in = self.token_expiry_minutes * 60  # Convert to seconds

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
            "metadata": user.metadata,
            "iat": now,
            "exp": now + timedelta(minutes=self.token_expiry_minutes),
        }

        access_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        return JWTToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user
        )

    async def validate_token(self, token: str) -> AuthenticationResult:
        """Validate a JWT jwt_token."""
        # Check if token is blacklisted (revoked)
        if token in self.revoked_tokens:
            return AuthenticationResult(success=False, error_message="Token has been revoked")
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            # Reconstruct user from jwt_token payload
            user = User(
                user_id=payload["user_id"],
                username=payload["username"],
                email=payload.get("email"),
                full_name=payload.get("full_name"),
                roles=payload.get("roles", []),
                metadata=payload.get("metadata", {}),
            )

            return AuthenticationResult(success=True, user=user)

        except ExpiredSignatureError:
            return AuthenticationResult(success=False, error_message="Token expired")
        except JWTError:
            return AuthenticationResult(success=False, error_message="Invalid jwt_token")

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResult:
        return AuthenticationResult(success=False, error_message="OAuth2 not supported by ListAuthBackend")

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a JWT token by adding it to the blacklist.
        
        Args:
            token: The JWT token to revoke
            
        Returns:
            True if successfully revoked, False if token is invalid
        """
        try:
            # Validate the token first to ensure it's a valid JWT
            jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Add to blacklist
            self.revoked_tokens.add(token)
            return True
            
        except JWTError:
            # Invalid token, cannot revoke
            return False
    
    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from the blacklist to prevent memory bloat.
        
        Returns:
            Number of tokens removed
        """
        tokens_to_remove = []
        
        for token in self.revoked_tokens:
            try:
                # Try to decode the token - if it raises ExpiredSignatureError, it's expired
                jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            except ExpiredSignatureError:
                # Token is expired, safe to remove from blacklist
                tokens_to_remove.append(token)
            except JWTError:
                # Token is invalid, remove it too
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            self.revoked_tokens.remove(token)
            
        return len(tokens_to_remove)



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
        # In real implementation, verify the OAuth2 jwt_token with the provider
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
        return AuthenticationResult(success=True, user=user)