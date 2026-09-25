"""The pure routing decision function: turns a Jev answer into the tier to run."""
from __future__ import annotations

from typing import Any

from jev_router_live.config import OVERRIDE_PATTERNS, TIER_NAMES, THRESHOLDS, rank_of


def detect_override(prompt: str | None) -> str | None:
    """The tier the user named explicitly in the prompt, or None."""
    text = prompt or ""
    for tier, pattern in OVERRIDE_PATTERNS:
        if pattern.search(text):
            return tier
    return None


def _clamp_to_available(tier: str, available: list[str]) -> str | None:
    """Nearest tier the account can actually run. Prefers stepping up rather than down so we
    never silently hand a hard task to a weaker model, but never steps up into `fable` (which
    bills extra usage credits) unless that is what was asked for."""
    if tier in available:
        return tier
    rank = rank_of(tier)
    up = [t for i, t in enumerate(TIER_NAMES) if i > rank and t in available and (t != "fable" or tier == "fable")]
    if up:
        return up[0]
    down = [t for i, t in enumerate(TIER_NAMES) if i < rank and t in available]
    return down[-1] if down else None


def decide(
    *,
    prompt: str | None,
    jev: dict[str, Any] | None,
    current: str,
    available: list[str],
    context_tokens: int = 0,
    first_turn: bool = False,
) -> dict[str, Any]:
    """Turns a Jev answer into the model we will actually run. Pure and total: any missing,
    malformed, or unavailable input falls back to the model already in use.

    Returns {"tier": str, "reason": str, "changed": bool}.
    """

    def settle(tier: str, reason: str) -> dict[str, Any]:
        final = _clamp_to_available(tier, available) or current
        why = reason if final == tier else f"{reason}+unavailable"
        return {
            "tier": final,
            "reason": f"{why}/no-change" if final == current else why,
            "changed": final != current,
        }

    override = detect_override(prompt)
    if override:
        return settle(override, "override")

    if not jev or jev.get("choice") not in TIER_NAMES:
        return settle(current, "jev-unavailable")

    target = jev["choice"]

    if jev.get("confidence", 1.0) < THRESHOLDS.min_confidence:
        if rank_of(target) < rank_of(current):
            return settle(current, "low-confidence-no-downgrade")
        ceiling = max(rank_of(current), rank_of(THRESHOLDS.uncertain_ceiling))
        if rank_of(target) > ceiling:
            return settle(TIER_NAMES[ceiling], "low-confidence-capped")

    # The cache-rebuild guard protects an already-pinned model; on a conversation's first
    # decision nothing is pinned yet, so a large (system-prompt-heavy) context must not veto it.
    if not first_turn and rank_of(target) < rank_of(current) and context_tokens > THRESHOLDS.downgrade_max_context_tokens:
        return settle(current, "downgrade-not-worth-cache-rebuild")

    return settle(target, "jev")
