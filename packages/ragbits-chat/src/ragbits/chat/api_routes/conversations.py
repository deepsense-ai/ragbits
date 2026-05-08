"""FastAPI router that implements conversation endpoints.

The router always exposes authenticated conversation history endpoints and can
optionally expose sharing endpoints when ``share_persistence`` is configured.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ragbits.chat.api_routes.share_access import recipient_identifiers
from ragbits.chat.auth import User
from ragbits.chat.interface.types import (
    ConversationDetail,
    ConversationInteractionData,
    ConversationMeta,
    ConversationShareResponse,
    ShareConversationRequest,
)
from ragbits.chat.persistence.base import HistoryPersistenceStrategy, SharePersistenceStrategy

RequireUser = Callable[[Request], Awaitable[User]]


def build_conversations_router(  # noqa: PLR0915
    history_persistence: HistoryPersistenceStrategy,
    require_user: RequireUser,
    share_persistence: SharePersistenceStrategy | None = None,
) -> APIRouter:
    """Create an :class:`APIRouter` exposing conversation endpoints.

    Args:
        history_persistence: History persistence with ownership/listing support.
        require_user: Dependency that returns the authenticated user or raises
            ``HTTPException(401)``.
        share_persistence: Optional share persistence strategy. When provided,
            share-management and shared-conversation access endpoints are enabled.
    """
    router = APIRouter()
    authed_user: Any = Depends(require_user)

    async def require_owner(conversation_id: str, user: User) -> None:
        owner = await history_persistence.get_conversation_owner(conversation_id)
        if owner is None or owner != user.user_id:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    @router.get("/api/conversations", response_model=list[ConversationMeta])
    async def list_conversations(user: User = authed_user) -> list[ConversationMeta]:
        owned = await history_persistence.list_conversations(user.user_id)
        owned_ids = {c["id"] for c in owned}
        shared_rows: list[dict[str, Any]] = []
        if share_persistence is not None:
            shared_rows = await share_persistence.list_shared_with_me(recipient_identifiers(user))
            shared_rows = [r for r in shared_rows if r["conversation_id"] not in owned_ids]

        all_ids = [c["id"] for c in owned] + [r["conversation_id"] for r in shared_rows]
        summaries = await history_persistence.get_conversation_summaries(all_ids)

        owned_metas = [
            ConversationMeta(
                conversation_id=c["id"],
                created_at=str(c["created_at"]) if c.get("created_at") else "",
                summary=summaries.get(c["id"]),
            )
            for c in owned
        ]
        shared_metas = [
            ConversationMeta(
                conversation_id=r["conversation_id"],
                created_at=str(r["shared_at"]) if r.get("shared_at") else "",
                summary=summaries.get(r["conversation_id"]),
                is_shared=True,
                shared_by=r["owner_id"],
            )
            for r in shared_rows
        ]
        return owned_metas + shared_metas

    @router.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
    async def get_conversation(conversation_id: str, user: User = authed_user) -> ConversationDetail:
        owner = await history_persistence.get_conversation_owner(conversation_id)
        is_shared = False
        shared_by: str | None = None
        is_owner = owner is not None and owner == user.user_id
        if not is_owner:
            if share_persistence is None:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            if not await share_persistence.can_access(conversation_id, recipient_identifiers(user)):
                raise HTTPException(status_code=404, detail="Conversation not found.")
            is_shared = True
            shared_by = owner

        interactions = await history_persistence.get_conversation_interactions(conversation_id)
        messages = [
            ConversationInteractionData(
                message_id=interaction.get("message_id"),
                message=str(interaction.get("message", "")),
                response=str(interaction.get("response", "")),
            )
            for interaction in interactions
        ]
        shares: list[ConversationShareResponse] | None = None
        if is_owner and share_persistence is not None:
            raw_shares = await share_persistence.get_shares(conversation_id, user.user_id)
            shares = [
                ConversationShareResponse(
                    recipient=s["recipient"],
                    shared_at=str(s["shared_at"]) if s.get("shared_at") else "",
                )
                for s in raw_shares
            ]
        return ConversationDetail(
            conversation_id=conversation_id,
            messages=messages,
            is_shared=is_shared,
            shared_by=shared_by,
            shares=shares,
        )

    @router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_conversation(conversation_id: str, user: User = authed_user) -> Response:
        await require_owner(conversation_id, user)
        await history_persistence.delete_conversation(conversation_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if share_persistence is not None:

        @router.put("/api/conversations/{conversation_id}/shares", response_model=list[ConversationShareResponse])
        async def update_shares(
            conversation_id: str,
            body: ShareConversationRequest,
            user: User = authed_user,
        ) -> list[ConversationShareResponse]:
            await require_owner(conversation_id, user)
            new_recipients = set(body.recipients)
            existing = await share_persistence.get_shares(conversation_id, user.user_id)
            existing_recipients = {s["recipient"] for s in existing}
            to_add = list(new_recipients - existing_recipients)
            to_remove = list(existing_recipients - new_recipients)
            if to_remove:
                await share_persistence.remove_shares(conversation_id, user.user_id, to_remove)
            if to_add:
                await share_persistence.set_shares(conversation_id, user.user_id, to_add)
            updated = await share_persistence.get_shares(conversation_id, user.user_id)
            return [
                ConversationShareResponse(
                    recipient=s["recipient"],
                    shared_at=str(s["shared_at"]) if s.get("shared_at") else "",
                )
                for s in updated
            ]

        @router.delete(
            "/api/conversations/{conversation_id}/shares/{recipient}",
            status_code=status.HTTP_204_NO_CONTENT,
        )
        async def revoke_share(
            conversation_id: str,
            recipient: str,
            user: User = authed_user,
        ) -> Response:
            await require_owner(conversation_id, user)
            await share_persistence.remove_shares(conversation_id, user.user_id, [recipient])
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        @router.delete("/api/shared/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def dismiss_share(conversation_id: str, user: User = authed_user) -> Response:
            if not await share_persistence.hide_share(conversation_id, recipient_identifiers(user)):
                raise HTTPException(status_code=404, detail="Shared conversation not found.")
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


def build_share_router(
    history_persistence: HistoryPersistenceStrategy,
    share_persistence: SharePersistenceStrategy,
    require_user: RequireUser,
) -> APIRouter:
    """Backward-compatible wrapper for existing share-router imports."""
    return build_conversations_router(
        history_persistence=history_persistence,
        require_user=require_user,
        share_persistence=share_persistence,
    )
