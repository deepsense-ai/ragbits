"""
Estimated LLM usage cost in USD from token counts.

Rates are **approximate** public pay-as-you-go list prices per million tokens
(input, output), aligned with vendor documentation. They exclude discounts
(batch, caching, enterprise), regional premiums, and free tiers. Unknown models
return ``0.0`` so callers should treat estimates as non-authoritative.

References (as of early 2026):

- https://platform.openai.com/docs/pricing
- https://docs.anthropic.com/en/docs/about-claude/pricing
- https://ai.google.dev/gemini-api/docs/pricing
"""

from __future__ import annotations

from typing import Literal

Provider = Literal["openai", "anthropic", "gemini"]

# (model_id prefix, input USD per 1M tokens, output USD per 1M tokens)
# Prefixes are matched longest-first against the normalized model id.
_OPENAI_RATES: list[tuple[str, float, float]] = [
    ("gpt-4.1-mini", 0.40, 1.60),
    ("gpt-4.1", 2.00, 8.00),
    ("gpt-4o-mini", 0.15, 0.60),
    ("gpt-4o", 2.50, 10.00),
    ("chatgpt-4o-latest", 2.50, 10.00),
    ("gpt-4-0125-preview", 10.00, 30.00),
    ("gpt-4-1106-preview", 10.00, 30.00),
    ("gpt-4-turbo", 10.00, 30.00),
    ("gpt-4-vision-preview", 10.00, 30.00),
    ("gpt-4-32k", 60.00, 120.00),
    ("gpt-4", 30.00, 60.00),
    ("gpt-3.5-turbo", 0.50, 1.50),
    ("o3-mini", 1.10, 4.40),
    ("o4-mini", 1.10, 4.40),
    ("o3-pro", 20.00, 80.00),
    ("o3", 2.00, 8.00),
    ("o1-mini", 3.00, 12.00),
    ("o1-pro", 150.00, 600.00),
    ("o1-preview", 15.00, 60.00),
    ("o1", 15.00, 60.00),
]

_ANTHROPIC_RATES: list[tuple[str, float, float]] = [
    ("claude-opus-4-7", 5.00, 25.00),
    ("claude-opus-4-6", 5.00, 25.00),
    ("claude-opus-4-5", 5.00, 25.00),
    ("claude-opus-4-1", 15.00, 75.00),
    ("claude-opus-4", 15.00, 75.00),
    ("claude-sonnet-4-6", 3.00, 15.00),
    ("claude-sonnet-4-5", 3.00, 15.00),
    ("claude-sonnet-4", 3.00, 15.00),
    ("claude-sonnet-3-7", 3.00, 15.00),
    ("claude-haiku-4-5", 1.00, 5.00),
    ("claude-haiku-3-5", 0.80, 4.00),
    ("claude-haiku-3", 0.25, 1.25),
    ("claude-opus-3", 15.00, 75.00),
]

_GEMINI_RATES: list[tuple[str, float, float]] = [
    ("gemini-3.1-flash-lite", 0.25, 1.50),
    ("gemini-3.1-pro", 2.00, 12.00),
    ("gemini-3.1", 0.25, 1.50),
    ("gemini-2.5-flash-lite", 0.10, 0.40),
    ("gemini-2.5-flash", 0.30, 2.50),
    ("gemini-2.5-pro", 1.25, 10.00),
    ("gemini-2.0-flash-lite", 0.075, 0.30),
    ("gemini-2.0-flash", 0.10, 0.40),
    ("gemini-1.5-pro", 1.25, 5.00),
    ("gemini-1.5-flash", 0.075, 0.30),
    ("gemini-1.0-pro", 0.50, 1.50),
    ("gemini-pro", 0.50, 1.50),
]


def _normalize_model_name(model_name: str) -> str:
    m = model_name.strip().lower()
    if "/" in m:
        _, _, rest = m.partition("/")
        m = rest
    if m.startswith("models/"):
        m = m.removeprefix("models/")
    return m


def _sorted_rates(rates: list[tuple[str, float, float]]) -> list[tuple[str, float, float]]:
    return sorted(rates, key=lambda row: len(row[0]), reverse=True)


_OPENAI_RATES_SORTED = _sorted_rates(_OPENAI_RATES)
_ANTHROPIC_RATES_SORTED = _sorted_rates(_ANTHROPIC_RATES)
_GEMINI_RATES_SORTED = _sorted_rates(_GEMINI_RATES)


def lookup_llm_token_rates_usd_per_million(provider: Provider, model_name: str) -> tuple[float, float] | None:
    """
    Returns (input_usd_per_million, output_usd_per_million) for a model, or None if unknown.
    """
    model = _normalize_model_name(model_name)
    if not model:
        return None

    table: list[tuple[str, float, float]]
    if provider == "openai":
        table = _OPENAI_RATES_SORTED
    elif provider == "anthropic":
        table = _ANTHROPIC_RATES_SORTED
    elif provider == "gemini":
        table = _GEMINI_RATES_SORTED
    else:
        return None

    for prefix, input_per_m, output_per_m in table:
        if model == prefix or model.startswith(prefix):
            return input_per_m, output_per_m
    return None


def estimate_llm_cost_usd(
    provider: Provider,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Estimated USD cost from token counts using public list prices.

    Unknown models yield ``0.0``. Negative token counts are clamped to zero.
    """
    rates = lookup_llm_token_rates_usd_per_million(provider, model_name)
    if rates is None:
        return 0.0
    input_per_m, output_per_m = rates
    pt = max(0, prompt_tokens)
    ct = max(0, completion_tokens)
    return pt * (input_per_m / 1_000_000) + ct * (output_per_m / 1_000_000)
