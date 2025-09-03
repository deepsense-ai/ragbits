"""
Model provider for ragbits-chat Pydantic models.

This module provides the RagbitsChatModelProvider class for importing and organizing
Pydantic models from the ragbits-chat package.
"""

from enum import Enum
from typing import cast

from pydantic import BaseModel

from ragbits.chat.interface.types import AuthType


class RagbitsChatModelProvider:
    """
    Provider for importing and organizing ragbits-chat Pydantic models.

    This provider handles the import of all Pydantic models from ragbits-chat package,
    provides caching for performance, and organizes models into logical categories.
    """

    def __init__(self) -> None:
        self._models_cache: dict[str, type[BaseModel | Enum]] | None = None
        self._categories_cache: dict[str, list[str]] | None = None

    def get_models(self) -> dict[str, type[BaseModel | Enum]]:
        """
        Import and return all ragbits-chat models.

        Returns:
            Dictionary mapping model names to their classes

        Raises:
            RuntimeError: If models cannot be imported
        """
        if self._models_cache is not None:
            return self._models_cache

        try:
            from ragbits.chat.auth.types import (
                CredentialsLoginRequest,
                JWTToken,
                LoginRequest,
                LoginResponse,
                LogoutRequest,
                User,
            )
            from ragbits.chat.interface.forms import UserSettings
            from ragbits.chat.interface.types import (
                AuthenticationConfig,
                ChatContext,
                ChatMessageRequest,
                ChatResponseType,
                ChunkedContent,
                ConfigResponse,
                FeedbackConfig,
                FeedbackItem,
                FeedbackRequest,
                FeedbackResponse,
                FeedbackType,
                Image,
                LiveUpdate,
                LiveUpdateContent,
                LiveUpdateType,
                Message,
                MessageRole,
                MessageUsage,
                Reference,
                StateUpdate,
            )
            from ragbits.chat.interface.ui_customization import (
                HeaderCustomization,
                PageMetaCustomization,
                UICustomization,
            )

            self._models_cache = {
                # Enums
                "ChatResponseType": ChatResponseType,
                "FeedbackType": FeedbackType,
                "LiveUpdateType": LiveUpdateType,
                "MessageRole": MessageRole,
                # Core data models
                "ChatContext": ChatContext,
                "ChunkedContent": ChunkedContent,
                "LiveUpdate": LiveUpdate,
                "LiveUpdateContent": LiveUpdateContent,
                "Message": Message,
                "Reference": Reference,
                "ServerState": StateUpdate,
                "FeedbackItem": FeedbackItem,
                "Image": Image,
                "MessageUsage": MessageUsage,
                # Configuration models
                "HeaderCustomization": HeaderCustomization,
                "UICustomization": UICustomization,
                "PageMetaCustomization": PageMetaCustomization,
                "UserSettings": UserSettings,
                "FeedbackConfig": FeedbackConfig,  # Current from types.py (not deprecated forms.py)
                # API response models
                "ConfigResponse": ConfigResponse,
                "FeedbackResponse": FeedbackResponse,
                # API request models
                "ChatRequest": ChatMessageRequest,
                "FeedbackRequest": FeedbackRequest,
                # Auth
                "AuthType": AuthType,
                "AuthenticationConfig": AuthenticationConfig,
                "CredentialsLoginRequest": CredentialsLoginRequest,
                "JWTToken": JWTToken,
                "LoginRequest": LoginRequest,
                "LoginResponse": LoginResponse,
                "LogoutRequest": LogoutRequest,
                "User": User,
            }

            return self._models_cache

        except ImportError as e:
            raise RuntimeError(
                f"Error importing ragbits-chat models: {e}. "
                "Make sure the ragbits-chat package is properly installed."
            ) from e

    def get_categories(self) -> dict[str, list[str]]:
        """
        Get models organized by category.

        Returns:
            Dictionary mapping category names to lists of model names
        """
        if self._categories_cache is not None:
            return self._categories_cache

        self._categories_cache = {
            "enums": [model_name for model_name, model in self._models_cache.items() if issubclass(model, Enum)]
            if self._models_cache
            else [],
            "core_data": [
                "ChatContext",
                "ChunkedContent",
                "LiveUpdate",
                "LiveUpdateContent",
                "Message",
                "Reference",
                "ServerState",
                "FeedbackItem",
                "Image",
                "JWTToken",
                "User",
                "MessageUsage",
            ],
            "configuration": [
                "HeaderCustomization",
                "UICustomization",
                "UserSettings",
                "FeedbackConfig",
                "AuthenticationConfig",
            ],
            "responses": [
                "FeedbackResponse",
                "ConfigResponse",
                "LoginResponse",
            ],
            "requests": [
                "ChatRequest",
                "FeedbackRequest",
                "CredentialsLoginRequest",
                "LoginRequest",
                "LogoutRequest",
            ],
        }

        return self._categories_cache

    def get_models_by_category(self, category: str) -> dict[str, type[BaseModel | Enum]]:
        """
        Get models filtered by category.

        Args:
            category: Category name (enums, core_data, api, configuration)

        Returns:
            Dictionary of models in the specified category

        Raises:
            ValueError: If category is not recognized
        """
        all_models = self.get_models()
        categories = self.get_categories()

        if category not in categories:
            raise ValueError(f"Unknown category: {category}. Available: {list(categories.keys())}")

        return {name: all_models[name] for name in categories[category] if name in all_models}

    def get_enum_models(self) -> dict[str, type[Enum]]:
        """
        Get only enum models.

        Returns:
            Dictionary of enum models
        """
        return cast(dict[str, type[Enum]], self.get_models_by_category("enums"))

    def get_pydantic_models(self) -> dict[str, type[BaseModel | Enum]]:
        """
        Get only Pydantic models (excluding enums).

        Returns:
            Dictionary of Pydantic models
        """
        all_models = self.get_models()
        enum_names = set(self.get_categories()["enums"])
        return {name: model for name, model in all_models.items() if name not in enum_names}

    def clear_cache(self) -> None:
        """
        Clear the internal cache, forcing re-import on next access.

        This can be useful during development or testing.
        """
        self._models_cache = None
        self._categories_cache = None
