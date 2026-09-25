"""Opt-in integration test against the REAL JEV (TypeSafe System One) API.

Skipped unless both are set:

    JEV_LIVE_TESTS=1
    JEV_API_KEY=<a real key>

Run:  JEV_LIVE_TESTS=1 python -m pytest tests/live/test_live_jev_api.py -s -q

Proves prompt -> real JEV -> real response -> valid model decision, for a trivial, a medium
and a hard task, through the same client and policy the proxy uses. Prints the selected
model, confidence and latency; never the key.
"""
from __future__ import annotations

import os

import pytest

from jev_router_live.config import TIERS, available_tiers
from jev_router_live.policy import decide
from jev_router_live.stdlib_router import stdlib_ask_jev

pytestmark = pytest.mark.skipif(
    not (os.environ.get("JEV_LIVE_TESTS") == "1" and os.environ.get("JEV_API_KEY")),
    reason="live JEV test: set JEV_LIVE_TESTS=1 and JEV_API_KEY",
)

MODELS = [{"id": t.id, "tier": t.name, "description": t.id} for t in TIERS if t.name in available_tiers()]
TIER_OF = {m["id"]: m["tier"] for m in MODELS}

CASES = [
    ("trivial", "Rename the variable `x` to `count` in utils.py."),
    ("medium", "Add input validation to the signup form handler and write unit tests for the invalid cases."),
    (
        "hard",
        "Intermittently, about 1 in 200 requests deadlock under load in our connection pool after the "
        "async migration. Find the root cause across the pool, retry and cancellation code and fix it "
        "without breaking the public API.",
    ),
]


@pytest.mark.parametrize("label,prompt", CASES, ids=[c[0] for c in CASES])
def test_real_jev_returns_a_valid_decision(label, prompt):
    answer = stdlib_ask_jev(prompt=prompt, current=MODELS[-1]["id"], context_tokens=2000, models=MODELS)

    assert answer is not None, "real JEV call failed (see [jev] log line above for the reason)"
    assert answer["choice"] in TIER_OF, f"JEV chose a model that was not offered: {answer['choice']!r}"
    assert 0.0 <= answer["confidence"] <= 1.0
    for metric in ("taskComplexity", "reasoningRequired", "toolComplexity"):
        assert 0.0 <= answer["metrics"][metric] <= 1.0

    decision = decide(
        prompt=prompt,
        jev={**answer, "choice": TIER_OF[answer["choice"]]},
        current="opus",
        available=[m["tier"] for m in MODELS],
        context_tokens=2000,
        first_turn=True,
    )
    print(
        f"\n[live-jev] {label:8s} model={answer['choice']} tier={decision['tier']} "
        f"confidence={answer['confidence']:.2f} latency={answer['ms']}ms reason={decision['reason']}"
    )
