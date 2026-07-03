from decimal import Decimal

import pytest

from app.services.cost_tracker import ModelPricing, estimate_cost_usd


def test_estimate_cost_uses_separate_input_and_output_rates() -> None:
    cost = estimate_cost_usd("gpt-4o-mini", 1_000_000, 2_000_000)

    assert cost == Decimal("1.35000000")


def test_estimate_cost_rounds_to_database_scale() -> None:
    pricing = {
        "rounding-test": ModelPricing(
            input_usd_per_million_tokens=Decimal("0.005"),
            output_usd_per_million_tokens=Decimal("0"),
        )
    }

    assert estimate_cost_usd("rounding-test", 1, 0, pricing=pricing) == Decimal("0.00000001")


@pytest.mark.parametrize("input_tokens,output_tokens", [(None, 10), (10, None), (None, None)])
def test_missing_token_usage_returns_none(
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    assert estimate_cost_usd("gpt-4o-mini", input_tokens, output_tokens) is None


def test_unknown_model_returns_none() -> None:
    assert estimate_cost_usd("unknown-model", 10, 5) is None


def test_explicit_snapshot_alias_has_pricing() -> None:
    assert estimate_cost_usd("gpt-4o-mini-2024-07-18", 10, 4) == Decimal("0.00000390")


@pytest.mark.parametrize("input_tokens,output_tokens", [(-1, 0), (0, -1), (-1, None)])
def test_negative_token_usage_is_rejected(
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        estimate_cost_usd("gpt-4o-mini", input_tokens, output_tokens)
