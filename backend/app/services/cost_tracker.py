from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from types import MappingProxyType
from typing import Final

TOKENS_PER_MILLION: Final = Decimal("1000000")
COST_QUANTUM: Final = Decimal("0.00000001")


@dataclass(frozen=True, slots=True)
class ModelPricing:
    input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal


_GPT_4O_MINI_PRICING = ModelPricing(
    input_usd_per_million_tokens=Decimal("0.15"),
    output_usd_per_million_tokens=Decimal("0.60"),
)

# Pricing is intentionally static and explicit. Snapshot aliases must be added here rather
# than inheriting prices by prefix, which prevents future model variants from being mispriced.
MODEL_PRICING: Final[Mapping[str, ModelPricing]] = MappingProxyType(
    {
        "gpt-4o-mini": _GPT_4O_MINI_PRICING,
        "gpt-4o-mini-2024-07-18": _GPT_4O_MINI_PRICING,
    }
)


def estimate_cost_usd(
    model_name: str,
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    pricing: Mapping[str, ModelPricing] = MODEL_PRICING,
) -> Decimal | None:
    """Estimate request cost, or return None when usage or pricing is unavailable."""
    for token_count in (input_tokens, output_tokens):
        if token_count is not None and token_count < 0:
            raise ValueError("Token counts must be nonnegative")

    model_pricing = pricing.get(model_name)
    if input_tokens is None or output_tokens is None or model_pricing is None:
        return None

    input_cost = (
        Decimal(input_tokens) * model_pricing.input_usd_per_million_tokens
    ) / TOKENS_PER_MILLION
    output_cost = (
        Decimal(output_tokens) * model_pricing.output_usd_per_million_tokens
    ) / TOKENS_PER_MILLION
    return (input_cost + output_cost).quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)
