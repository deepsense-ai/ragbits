"""
Model provider for ragbits-chat Pydantic models.

This module provides the RagbitsChatModelProvider class for importing and organizing
Pydantic models from the ragbits-chat package.
"""

from typing import Dict, Type
from pydantic import BaseModel


class RagbitsChatModelProvider:
    """
    Provider for importing and organizing ragbits-chat Pydantic models.

    This provider handles the import of all Pydantic models from ragbits-chat package,
    provides caching for performance, and organizes models into logical categories.
    """

    def __init__(self):
        self._models_cache: Dict[str, Type[BaseModel]] | None = None
        self._categories_cache: Dict[str, list[str]] | None = None

    def get_models(self) -> Dict[str, Type[BaseModel]]:
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
            from ragbits.chat.interface.types import (
                ChatContext,
                ChatRequest,
                ChatResponseType,
                FeedbackResponse,
                FeedbackType,
                LiveUpdate,
                LiveUpdateContent,
                LiveUpdateType,
                Message,
                MessageRoleType,
                Reference,
                StateUpdate,
                ConfigResponse,
                FeedbackRequest,
                FeedbackConfig,
                FeedbackItem,
                Image,
            )
            from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
            from ragbits.chat.interface.forms import UserSettings

            self._models_cache = {
                # Enums
                "ChatResponseType": ChatResponseType,
                "FeedbackType": FeedbackType,
                "LiveUpdateType": LiveUpdateType,
                "MessageRoleType": MessageRoleType,

                # Core data models
                "ChatContext": ChatContext,
                "LiveUpdate": LiveUpdate,
                "LiveUpdateContent": LiveUpdateContent,
                "Message": Message,
                "Reference": Reference,
                "ServerState": StateUpdate,
                "FeedbackItem": FeedbackItem,
                "Image": Image,

                # Configuration models
                "HeaderCustomization": HeaderCustomization,
                "UICustomization": UICustomization,
                "UserSettings": UserSettings,
                "FeedbackConfig": FeedbackConfig,  # Current from types.py (not deprecated forms.py)

                # API response models
                "ConfigResponse": ConfigResponse,
                "FeedbackResponse": FeedbackResponse,

                # API request models
                "ChatRequest": ChatRequest,
                "FeedbackRequest": FeedbackRequest,
            }

            return self._models_cache

        except ImportError as e:
            raise RuntimeError(f"Error importing ragbits-chat models: {e}. "
                             "Make sure the ragbits-chat package is properly installed.")

    def get_categories(self) -> Dict[str, list[str]]:
        """
        Get models organized by category.

        Returns:
            Dictionary mapping category names to lists of model names
        """
        if self._categories_cache is not None:
            return self._categories_cache

        self._categories_cache = {
            "enums": ["ChatResponseType", "FeedbackType", "LiveUpdateType", "MessageRoleType"],
            "core_data": ["ChatContext", "LiveUpdate", "LiveUpdateContent", "Message", "Reference", "ServerState", "FeedbackItem"],
            "configuration": ["HeaderCustomization", "UICustomization", "UserSettings", "FeedbackConfig"],
            "responses": ["FeedbackResponse", "ConfigResponse"],
            "requests": ["ChatRequest", "FeedbackRequest"],
        }

        return self._categories_cache

    def get_models_by_category(self, category: str) -> Dict[str, Type[BaseModel]]:
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

    def get_enum_models(self) -> Dict[str, Type[BaseModel]]:
        """
        Get only enum models.

        Returns:
            Dictionary of enum models
        """
        return self.get_models_by_category("enums")

    def get_pydantic_models(self) -> Dict[str, Type[BaseModel]]:
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