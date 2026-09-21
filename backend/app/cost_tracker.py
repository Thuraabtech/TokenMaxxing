"""In-memory cost ledger. Resets on process restart -- fine for a prototype,
not a substitute for the AWS Budget alerts recommended in the blueprint.

Alongside actual spend, this tracks "saved" -- the gap between what a call
actually cost and what the same input/output tokens would have cost at the
high tier's price. That's the number the UI leads with: it's the honest,
defensible measure of what the router bought you, computed the same way for
every call (segmentation, routing, and assembly alike) rather than assumed.
"""

from threading import Lock

from app.config import settings

_lock = Lock()
_running_total_usd = 0.0
_running_saved_usd = 0.0
_tier_totals = {"low": 0.0, "medium": 0.0, "high": 0.0}
_tier_saved = {"low": 0.0, "medium": 0.0, "high": 0.0}
_tier_calls = {"low": 0, "medium": 0, "high": 0}


def price_call(tier: str, input_tokens: int, output_tokens: int) -> float:
    prices = settings.prices[tier]
    return input_tokens * prices["in"] / 1000 + output_tokens * prices["out"] / 1000


def record(tier: str, input_tokens: int, output_tokens: int) -> tuple[float, float]:
    """Records a call and returns (cost_usd, saved_usd)."""
    cost = price_call(tier, input_tokens, output_tokens)
    baseline = price_call("high", input_tokens, output_tokens)
    saved = max(baseline - cost, 0.0)

    global _running_total_usd, _running_saved_usd
    with _lock:
        _running_total_usd += cost
        _running_saved_usd += saved
        _tier_totals[tier] += cost
        _tier_saved[tier] += saved
        _tier_calls[tier] += 1
    return cost, saved


def snapshot() -> dict:
    with _lock:
        return {
            "running_total_usd": round(_running_total_usd, 6),
            "running_saved_usd": round(_running_saved_usd, 6),
            "tier_totals_usd": {k: round(v, 6) for k, v in _tier_totals.items()},
            "tier_saved_usd": {k: round(v, 6) for k, v in _tier_saved.items()},
            "tier_calls": dict(_tier_calls),
        }
