from datetime import datetime, timedelta, timezone

import pytest

from ragbits.chat.auth.session_store import InMemorySessionStore
from ragbits.chat.auth.types import Session, User


@pytest.fixture
def session_store():
    """Create a session store for testing."""
    return InMemorySessionStore()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        user_id="test-user-1",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        roles=["user"],
        metadata={},
    )


@pytest.fixture
def sample_session(sample_user: User):
    """Create a sample session for testing."""
    now = datetime.now(timezone.utc)
    return Session(
        session_id="",  # Will be generated
        user=sample_user,
        provider="credentials",
        oauth_token="",
        token_type="",
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_create_session(session_store: InMemorySessionStore, sample_session: Session) -> None:
        """Test creating a new session."""
        session_id = await session_store.create_session(sample_session)

        assert session_id is not None
        assert len(session_id) > 0
        assert session_id in session_store.sessions

    @pytest.mark.asyncio
    @staticmethod
    async def test_get_session_valid(session_store: InMemorySessionStore, sample_session: Session) -> None:
        """Test retrieving a valid session."""
        session_id = await session_store.create_session(sample_session)

        retrieved = await session_store.get_session(session_id)

        assert retrieved is not None
        assert retrieved.user.username == "testuser"
        assert retrieved.session_id == session_id

    @pytest.mark.asyncio
    @staticmethod
    async def test_get_session_not_found(session_store: InMemorySessionStore) -> None:
        """Test retrieving a non-existent session."""
        retrieved = await session_store.get_session("nonexistent-session-id")

        assert retrieved is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_get_session_expired(session_store: InMemorySessionStore, sample_user: User) -> None:
        """Test that expired sessions are not returned and are deleted."""
        now = datetime.now(timezone.utc)
        expired_session = Session(
            session_id="",
            user=sample_user,
            provider="credentials",
            oauth_token="",
            token_type="",
            created_at=now - timedelta(hours=48),
            expires_at=now - timedelta(hours=24),  # Expired
        )

        session_id = await session_store.create_session(expired_session)

        # Session should be in store
        assert session_id in session_store.sessions

        # Getting the session should return None and delete it
        retrieved = await session_store.get_session(session_id)

        assert retrieved is None
        assert session_id not in session_store.sessions

    @pytest.mark.asyncio
    @staticmethod
    async def test_delete_session_exists(session_store: InMemorySessionStore, sample_session: Session) -> None:
        """Test deleting an existing session."""
        session_id = await session_store.create_session(sample_session)

        success = await session_store.delete_session(session_id)

        assert success is True
        assert session_id not in session_store.sessions

    @pytest.mark.asyncio
    @staticmethod
    async def test_delete_session_not_found(session_store: InMemorySessionStore) -> None:
        """Test deleting a non-existent session."""
        success = await session_store.delete_session("nonexistent-session-id")

        assert success is False


class TestCleanupExpiredSessions:
    """Tests for cleanup_expired_sessions functionality."""

    @staticmethod
    def test_cleanup_no_expired_sessions(session_store: InMemorySessionStore, sample_user: User) -> None:
        """Test cleanup when there are no expired sessions."""
        now = datetime.now(timezone.utc)
        # Add valid sessions directly to the store
        for i in range(3):
            session_store.sessions[f"session-{i}"] = Session(
                session_id=f"session-{i}",
                user=sample_user,
                provider="credentials",
                oauth_token="",
                token_type="",
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )

        removed = session_store.cleanup_expired_sessions()

        assert removed == 0
        assert len(session_store.sessions) == 3

    @staticmethod
    def test_cleanup_all_expired_sessions(session_store: InMemorySessionStore, sample_user: User) -> None:
        """Test cleanup when all sessions are expired."""
        now = datetime.now(timezone.utc)
        # Add expired sessions directly to the store
        for i in range(3):
            session_store.sessions[f"session-{i}"] = Session(
                session_id=f"session-{i}",
                user=sample_user,
                provider="credentials",
                oauth_token="",
                token_type="",
                created_at=now - timedelta(hours=48),
                expires_at=now - timedelta(hours=24),  # Expired
            )

        removed = session_store.cleanup_expired_sessions()

        assert removed == 3
        assert len(session_store.sessions) == 0

    @staticmethod
    def test_cleanup_mixed_sessions(session_store: InMemorySessionStore, sample_user: User) -> None:
        """Test cleanup with mix of valid and expired sessions."""
        now = datetime.now(timezone.utc)

        # Add 2 valid sessions
        for i in range(2):
            session_store.sessions[f"valid-{i}"] = Session(
                session_id=f"valid-{i}",
                user=sample_user,
                provider="credentials",
                oauth_token="",
                token_type="",
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )

        # Add 3 expired sessions
        for i in range(3):
            session_store.sessions[f"expired-{i}"] = Session(
                session_id=f"expired-{i}",
                user=sample_user,
                provider="credentials",
                oauth_token="",
                token_type="",
                created_at=now - timedelta(hours=48),
                expires_at=now - timedelta(hours=24),  # Expired
            )

        removed = session_store.cleanup_expired_sessions()

        assert removed == 3
        assert len(session_store.sessions) == 2
        assert "valid-0" in session_store.sessions
        assert "valid-1" in session_store.sessions
        assert "expired-0" not in session_store.sessions
        assert "expired-1" not in session_store.sessions
        assert "expired-2" not in session_store.sessions

    @staticmethod
    def test_cleanup_empty_store(session_store: InMemorySessionStore) -> None:
        """Test cleanup on an empty session store."""
        removed = session_store.cleanup_expired_sessions()

        assert removed == 0
        assert len(session_store.sessions) == 0
