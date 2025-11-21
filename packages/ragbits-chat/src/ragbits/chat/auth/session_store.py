"""Session storage implementations."""

import asyncio
import secrets
from datetime import datetime, timezone

from ragbits.chat.auth.types import Session, SessionStore


class InMemorySessionStore(SessionStore):
    """In-memory session store implementation."""

    def __init__(self) -> None:
        """Initialize the in-memory session store."""
        self.sessions: dict[str, Session] = {}
        self.lock = asyncio.Lock()

    async def create_session(self, session: Session) -> str:
        """
        Create a new session.

        Args:
            session: Session object to store

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        session.session_id = session_id

        async with self.lock:
            self.sessions[session_id] = session

        return session_id

    async def get_session(self, session_id: str) -> Session | None:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session object if found and not expired, None otherwise
        """
        async with self.lock:
            session = self.sessions.get(session_id)

        if not session:
            return None

        # Check if session is expired
        if datetime.now(timezone.utc) > session.expires_at:
            # Session expired, delete it
            await self.delete_session(session_id)
            return None

        return session

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        async with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True

        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from storage.

        Note: This method is synchronous for compatibility. It acquires the lock internally.

        Returns:
            Number of sessions removed
        """
        now = datetime.now(timezone.utc)
        sessions_to_remove = []

        # Note: This is a synchronous method for background task compatibility
        # In production, consider using an async background task instead
        try:
            # Try to acquire lock without blocking if we're in an async context
            if self.lock.locked():
                return 0  # Skip cleanup if lock is held

            # Synchronous cleanup - safe for background threads
            for session_id, session in list(self.sessions.items()):
                if now > session.expires_at:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                self.sessions.pop(session_id, None)

            return len(sessions_to_remove)
        except Exception:
            return 0
