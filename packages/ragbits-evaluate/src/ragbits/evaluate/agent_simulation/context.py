"""Context models for agent simulation scenarios."""

from dataclasses import dataclass, field
from typing import Any

DEFAULT_MAX_ITEMS_IN_PROMPT = 15


@dataclass
class DomainContext:
    """Domain-specific context for goal checking and simulation.

    Provides additional context to the GoalChecker to avoid false negatives
    from value interpretation differences or missing domain knowledge.

    The context is intentionally generic - use the `metadata` field for any
    domain-specific information that doesn't fit the standard fields.

    Example:
        >>> context = DomainContext(
        ...     domain_type="customer_support",
        ...     locale="en_US",
        ...     metadata={"ticket_statuses": ["open", "pending", "resolved"]},
        ... )
        >>> result = await goal_checker.is_task_achieved(task, history, context=context)
    """

    domain_type: str
    """Type of domain (e.g., "customer_support", "booking", "search", "qa")."""

    locale: str = "en_US"
    """Locale for language and formatting (e.g., "en_US", "de_DE")."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary domain-specific metadata for goal checking context."""

    def format_for_prompt(self) -> str:
        """Format context for inclusion in LLM prompts.

        Returns:
            Formatted string suitable for prompt injection.
        """
        parts = [
            f"Domain: {self.domain_type}",
            f"Locale: {self.locale}",
        ]

        if self.metadata:
            parts.append("Additional context:")
            for key, value in self.metadata.items():
                if isinstance(value, list) and len(value) > DEFAULT_MAX_ITEMS_IN_PROMPT:
                    truncated = value[:DEFAULT_MAX_ITEMS_IN_PROMPT]
                    parts.append(f"  {key}: {truncated} ... and {len(value) - DEFAULT_MAX_ITEMS_IN_PROMPT} more")
                else:
                    parts.append(f"  {key}: {value}")

        return "\n".join(parts)


@dataclass
class DataSnapshot:
    """Sample of available data to ground simulated user requests.

    Provides the simulated user with knowledge of what data actually exists,
    preventing unrealistic requests for non-existent entities.

    The snapshot is intentionally generic - store any domain-specific data
    in the `entities` dict with descriptive keys.

    Example:
        >>> snapshot = DataSnapshot(
        ...     entities={
        ...         "available_topics": ["billing", "technical", "returns"],
        ...         "sample_users": [{"id": "u1", "name": "John"}],
        ...     },
        ...     description="Customer support knowledge base",
        ... )
        >>> # SimulatedUser will only reference items from this data
    """

    entities: dict[str, list[Any]] = field(default_factory=dict)
    """Named collections of available entities (e.g., {"users": [...], "documents": [...]})."""

    description: str = ""
    """Optional description of the data snapshot for context."""

    def format_for_prompt(self, max_items: int = DEFAULT_MAX_ITEMS_IN_PROMPT) -> str:
        """Format data snapshot for inclusion in LLM prompts.

        Args:
            max_items: Maximum number of items to include per entity type.

        Returns:
            Formatted string suitable for prompt injection.
        """
        parts = []

        if self.description:
            parts.append(f"Context: {self.description}")

        for entity_name, entity_list in self.entities.items():
            if not entity_list:
                continue

            truncated = entity_list[:max_items]
            # Format items - if dicts with 'name', use that; otherwise str()
            formatted_items = []
            for item in truncated:
                if isinstance(item, dict) and "name" in item:
                    formatted_items.append(item["name"])
                else:
                    formatted_items.append(str(item))

            parts.append(f"{entity_name}: {', '.join(formatted_items)}")
            if len(entity_list) > max_items:
                parts.append(f"  ... and {len(entity_list) - max_items} more")

        return "\n".join(parts)
