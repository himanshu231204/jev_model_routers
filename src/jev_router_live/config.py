"""Every routing decision knob lives here, so the whole policy is reviewable in one file.

Direct port of gargpratyush/jev-router's ``src/config.mjs``.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tier:
    name: str
    id: str
    family: str
    thinking: bool
    effort: bool


# Model tiers, cheapest first. `id` is what goes into the API request body; `family` is the
# substring used to recognise whatever model Claude Code asked for, which may be an older
# version within the same tier such as `claude-sonnet-4-6`. The capability flags mirror the
# Agent SDK's model catalogue: Haiku supports neither adaptive thinking nor effort, so those
# fields have to be stripped when routing down to it.
TIERS: list[Tier] = [
    Tier("haiku", "claude-haiku-4-5-20251001", "haiku", thinking=False, effort=False),
    Tier("sonnet", "claude-sonnet-5", "sonnet", thinking=True, effort=True),
    Tier("opus", "claude-opus-5", "opus", thinking=True, effort=True),
    Tier("fable", "claude-fable-5-1", "fable", thinking=True, effort=True),
]

TIER_NAMES: list[str] = [t.name for t in TIERS]


def rank_of(name: str | None) -> int:
    try:
        return TIER_NAMES.index(name)  # type: ignore[arg-type]
    except ValueError:
        return -1


def id_of(name: str) -> str | None:
    return next((t.id for t in TIERS if t.name == name), None)


def tier_spec(name: str) -> Tier | None:
    return next((t for t in TIERS if t.name == name), None)


# Sentinel model id offered as an extra row in Claude Code's /model picker. Claude Code sends
# it verbatim because it does not validate model names behind a custom base URL, so its
# presence in a request is an exact signal that the user wants this turn routed. Any other
# model means the user picked one themselves and it must be passed straight through.
AUTO_MODEL = "jev-router"


def is_auto(model: str | None) -> bool:
    return model == AUTO_MODEL


def tier_of(model: str | None) -> str | None:
    """Tier name for a model string the CLI sent, or None if we don't recognise it."""
    if not isinstance(model, str):
        return None
    return next((t.name for t in TIERS if t.family in model), None)


def available_tiers() -> list[str]:
    """Fable bills extra usage credits, so it is opt-in; everything else is a normal subscription."""
    return [n for n in TIER_NAMES if n != "fable" or os.environ.get("JEV_ALLOW_FABLE") == "1"]


@dataclass(frozen=True)
class Thresholds:
    # Below this Jev confidence we refuse to downgrade and cap upgrades at `uncertain_ceiling`.
    min_confidence: float = 0.3
    # Safest tier to land on when Jev is unsure.
    uncertain_ceiling: str = "sonnet"
    # Switching models invalidates the prompt cache; the next turn re-sends the whole
    # conversation. Measured at ~23.6k cache-creation tokens switching into Opus, so a
    # downgrade only pays off while the conversation is still small.
    downgrade_max_context_tokens: int = 20000
    # Per-attempt Jev HTTP timeout and the hard wall-clock deadline for the whole routing call.
    # Measured: ~300-350ms warm, ~900-1000ms on the first call (TLS handshake), so the deadline
    # leaves room for one retry after a cold-start timeout.
    jev_timeout_ms: int = 1500
    jev_deadline_ms: int = 3000
    jev_max_retries: int = 1


THRESHOLDS = Thresholds()

CONTEXT_WINDOW_TOKENS = 200_000

_COMPLEXITY_SCALE = [
    "None",
    "Very low",
    "Low",
    "Some",
    "Moderate",
    "Moderate to high",
    "High",
    "Very high",
    "Severe",
    "Extreme",
]

COMPLEXITY_MAX_SCORE = len(_COMPLEXITY_SCALE) - 1

_OVERRIDE_WORDS = {
    "haiku": "haiku|fast|luna",
    "sonnet": "sonnet|balanced|terra",
    "opus": "opus|strong|sol",
    "fable": "fable|long|astra",
}

# Phrases that mean "the human already decided", checked against the raw prompt.
OVERRIDE_PATTERNS: list[tuple[str, re.Pattern]] = [
    (t.name, re.compile(rf"\b(?:use|switch to|with|on)\s+(?:{_OVERRIDE_WORDS[t.name]})\b", re.I))
    for t in TIERS
]

QUESTIONS = {
    "task_complexity": {
        "type": "score",
        "prompt": "How complex is the coding task overall, including ambiguity, scope, and blast radius?",
        "scale": _COMPLEXITY_SCALE,
    },
    "reasoning_required": {
        "type": "score",
        "prompt": "How much reasoning is required to complete the request correctly in one pass?",
        "scale": _COMPLEXITY_SCALE,
    },
    "tool_complexity": {
        "type": "score",
        "prompt": "How complex is the tool use required, from no tools to many coordinated or stateful operations?",
        "scale": _COMPLEXITY_SCALE,
    },
}

_GUIDANCE = {
    "haiku": {
        "what": "Trivial, mechanical, or purely factual work.",
        "signals": ["Rename, reformat, comment, or run one obvious command"],
        "not_for": "Design judgement or multi-file reasoning.",
    },
    "sonnet": {
        "what": "Ordinary day-to-day engineering with a clear, bounded shape.",
        "signals": ["Implement a specified function, test existing behaviour, or fix an understood local bug"],
        "not_for": "Open-ended architecture, subtle concurrency, or unknown-cause debugging.",
    },
    "opus": {
        "what": "Hard reasoning, ambiguity, or high blast radius.",
        "signals": ["Unknown-cause debugging, cross-module design, security, auth, concurrency, or migrations"],
        "not_for": "Routine work with a clear implementation.",
    },
    "fable": {
        "what": "Very large or long-running work beyond a normal focused session.",
        "signals": ["Whole-repo migration, unusually large context, or multi-hour autonomous execution"],
        "not_for": "Anything a strong model can finish in one focused session.",
    },
}


def question_for_models(models: list[dict]) -> dict:
    """Build a Jev choice question from the exact models available to this account and CLI."""
    options = {}
    for m in models:
        guidance = _GUIDANCE.get(m["tier"], {})
        options[m["id"]] = {"model": m.get("description") or m["id"], **guidance}
    return {
        "type": "choice",
        "prompt": [
            "Pick the cheapest exact model that can fully complete this coding request in one "
            "pass, without retrying on a stronger model.",
            "Treat different model versions as separate choices. Judge required reasoning, not "
            "requested reply length.",
        ],
        "options": options,
    }


def should_use_exact_model(reason: str, chosen_tier: str | None, final_tier: str) -> bool:
    """Whether policy accepted Jev's exact model, including a version change within one tier."""
    return reason in ("jev", "jev/no-change") and chosen_tier == final_tier
