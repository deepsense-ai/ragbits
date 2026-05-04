from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OAuthTokenData:
    access_token: str
    expires_at: datetime | None = None
    refresh_token: str | None = None


class InMemoryOAuthTokenStore:
    """In-memory store mapping session_id → OAuth token data per scope group.

    Populated by the incremental OAuth callback in ``RagbitsAPI`` and read by
    ``ChatTool`` implementations that need to call Google APIs.
    """

    def __init__(self) -> None:
        # session_id -> scope_group -> OAuthTokenData
        self._tokens: dict[str, dict[str, OAuthTokenData]] = {}

    def save(self, session_id: str, scope_group: str, token_data: OAuthTokenData) -> None:
        self._tokens.setdefault(session_id, {})[scope_group] = token_data

    def get(self, session_id: str, scope_group: str) -> OAuthTokenData | None:
        return self._tokens.get(session_id, {}).get(scope_group)

    def get_access_token(self, session_id: str, scope_group: str) -> str | None:
        data = self.get(session_id, scope_group)
        return data.access_token if data else None


# Module-level singleton — shared between api.py (writes) and tools (reads).
_token_store = InMemoryOAuthTokenStore()


def get_token_store() -> InMemoryOAuthTokenStore:
    return _token_store
