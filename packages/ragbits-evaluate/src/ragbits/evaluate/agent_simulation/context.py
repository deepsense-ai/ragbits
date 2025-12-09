"""Context models for agent simulation scenarios."""

from dataclasses import dataclass, field
from typing import Any

MAX_MERCHANTS_IN_PROMPT = 5
MAX_PRODUCTS_IN_PROMPT = 10


@dataclass
class DomainContext:
    """Domain-specific context for goal checking and simulation.

    Provides additional context to the GoalChecker to avoid false negatives
    from currency confusion, locale differences, or missing domain knowledge.

    Example:
        >>> context = DomainContext(
        ...     domain_type="retail", currency="SAR", locale="ar_SA", business_rules={"prices_include_vat": True}
        ... )
        >>> result = await goal_checker.is_task_achieved(task, history, context=context)
    """

    domain_type: str
    """Type of domain: "food", "retail", "travel", "groceries", etc."""

    currency: str = "USD"
    """Currency code for price interpretation (e.g., "USD", "SAR", "EUR")."""

    locale: str = "en_US"
    """Locale for language and formatting (e.g., "en_US", "ar_SA")."""

    available_merchants: list[dict[str, Any]] = field(default_factory=list)
    """List of available merchants/vendors for validation."""

    available_products: list[dict[str, Any]] = field(default_factory=list)
    """List of available products for validation."""

    business_rules: dict[str, Any] = field(default_factory=dict)
    """Domain-specific business rules (e.g., {"min_order": 50, "delivery_fee": 10})."""

    def format_for_prompt(self) -> str:
        """Format context for inclusion in LLM prompts.

        Returns:
            Formatted string suitable for prompt injection.
        """
        parts = [
            f"Domain: {self.domain_type}",
            f"Currency: {self.currency}",
            f"Locale: {self.locale}",
        ]

        if self.business_rules:
            rules_str = ", ".join(f"{k}={v}" for k, v in self.business_rules.items())
            parts.append(f"Business Rules: {rules_str}")

        if self.available_merchants:
            merchant_names = [m.get("name", str(m)) for m in self.available_merchants[:MAX_MERCHANTS_IN_PROMPT]]
            parts.append(f"Available Merchants: {', '.join(merchant_names)}")
            if len(self.available_merchants) > MAX_MERCHANTS_IN_PROMPT:
                parts.append(f"  ... and {len(self.available_merchants) - MAX_MERCHANTS_IN_PROMPT} more")

        if self.available_products:
            product_names = [p.get("name", str(p)) for p in self.available_products[:MAX_PRODUCTS_IN_PROMPT]]
            parts.append(f"Sample Products: {', '.join(product_names)}")
            if len(self.available_products) > MAX_PRODUCTS_IN_PROMPT:
                parts.append(f"  ... and {len(self.available_products) - MAX_PRODUCTS_IN_PROMPT} more")

        return "\n".join(parts)
