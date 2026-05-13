import pytest

from ragbits.core.llms.pricing import estimate_llm_cost_usd, lookup_llm_token_rates_usd_per_million


@pytest.mark.parametrize(
    ("model", "expected_input_per_m", "expected_output_per_m"),
    [
        ("gpt-4o-mini", 0.15, 0.60),
        ("openai/gpt-4o-mini", 0.15, 0.60),
        ("gpt-4o", 2.50, 10.00),
        ("gpt-4-0125-preview", 10.00, 30.00),
    ],
)
def test_openai_rate_lookup(model: str, expected_input_per_m: float, expected_output_per_m: float) -> None:
    rates = lookup_llm_token_rates_usd_per_million("openai", model)
    assert rates is not None
    assert rates[0] == pytest.approx(expected_input_per_m)
    assert rates[1] == pytest.approx(expected_output_per_m)


def test_openai_gpt4o_mini_cost() -> None:
    # 1k in @ $0.15/M + 500 out @ $0.60/M
    cost = estimate_llm_cost_usd("openai", "gpt-4o-mini", 1000, 500)
    assert cost == pytest.approx(1000 * 0.15 / 1_000_000 + 500 * 0.60 / 1_000_000)


def test_anthropic_haiku_45_prefix() -> None:
    rates = lookup_llm_token_rates_usd_per_million("anthropic", "claude-haiku-4-5-20251001")
    assert rates == (1.00, 5.00)


def test_gemini_flash_normalization() -> None:
    rates = lookup_llm_token_rates_usd_per_million("gemini", "models/gemini-2.5-flash")
    assert rates == (0.30, 2.50)


def test_unknown_model_returns_zero() -> None:
    assert estimate_llm_cost_usd("openai", "unknown-custom-model", 1000, 1000) == 0.0


def test_negative_tokens_clamped() -> None:
    assert estimate_llm_cost_usd("openai", "gpt-4o-mini", -100, 1000) == pytest.approx(1000 * 0.60 / 1_000_000)
