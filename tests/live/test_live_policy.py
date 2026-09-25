from jev_router_live.policy import decide, detect_override


def test_detect_override():
    assert detect_override("use haiku please") == "haiku"
    assert detect_override("switch to strong mode") == "opus"
    assert detect_override("nothing special here") is None


def test_decide_override_beats_jev():
    result = decide(
        prompt="use opus for this",
        jev={"choice": "haiku", "confidence": 0.9},
        current="haiku",
        available=["haiku", "sonnet", "opus"],
    )
    assert result["tier"] == "opus"
    assert result["reason"] == "override"
    assert result["changed"] is True


def test_decide_jev_unavailable_keeps_current():
    result = decide(prompt="do the thing", jev=None, current="sonnet", available=["haiku", "sonnet", "opus"])
    assert result["tier"] == "sonnet"
    assert result["reason"] == "jev-unavailable/no-change"
    assert result["changed"] is False


def test_decide_low_confidence_refuses_downgrade():
    result = decide(
        prompt="fix this",
        jev={"choice": "haiku", "confidence": 0.1},
        current="opus",
        available=["haiku", "sonnet", "opus"],
    )
    assert result["tier"] == "opus"
    assert result["reason"] == "low-confidence-no-downgrade/no-change"


def test_decide_low_confidence_caps_upgrade():
    result = decide(
        prompt="fix this",
        jev={"choice": "opus", "confidence": 0.1},
        current="haiku",
        available=["haiku", "sonnet", "opus"],
    )
    assert result["tier"] == "sonnet"
    assert result["reason"] == "low-confidence-capped"


def test_decide_downgrade_blocked_by_large_context():
    result = decide(
        prompt="fix this",
        jev={"choice": "haiku", "confidence": 0.95},
        current="opus",
        available=["haiku", "sonnet", "opus"],
        context_tokens=50_000,
    )
    assert result["tier"] == "opus"
    assert result["reason"] == "downgrade-not-worth-cache-rebuild/no-change"


def test_decide_first_turn_allows_downgrade_despite_large_context():
    """The cache-rebuild guard exists to protect an already-pinned model. On a conversation's
    first decision nothing is pinned yet, so a large (system-prompt-heavy) context must not
    block Jev's downgrade."""
    result = decide(
        prompt="rename x to count",
        jev={"choice": "haiku", "confidence": 0.95},
        current="opus",
        available=["haiku", "sonnet", "opus"],
        context_tokens=50_000,
        first_turn=True,
    )
    assert result["tier"] == "haiku"
    assert result["reason"] == "jev"


def test_decide_subsequent_turn_still_blocks_large_context_downgrade():
    result = decide(
        prompt="rename x to count",
        jev={"choice": "haiku", "confidence": 0.95},
        current="opus",
        available=["haiku", "sonnet", "opus"],
        context_tokens=50_000,
        first_turn=False,
    )
    assert result["tier"] == "opus"
    assert result["reason"] == "downgrade-not-worth-cache-rebuild/no-change"


def test_decide_first_turn_higher_or_equal_tier_unchanged():
    upgraded = decide(
        prompt="hard task",
        jev={"choice": "opus", "confidence": 0.9},
        current="haiku",
        available=["haiku", "sonnet", "opus"],
        context_tokens=50_000,
        first_turn=True,
    )
    assert upgraded == {"tier": "opus", "reason": "jev", "changed": True}

    same = decide(
        prompt="anything",
        jev={"choice": "opus", "confidence": 0.9},
        current="opus",
        available=["haiku", "sonnet", "opus"],
        context_tokens=50_000,
        first_turn=True,
    )
    assert same == {"tier": "opus", "reason": "jev/no-change", "changed": False}


def test_decide_plain_jev_recommendation():
    result = decide(
        prompt="fix this",
        jev={"choice": "sonnet", "confidence": 0.9},
        current="haiku",
        available=["haiku", "sonnet", "opus"],
    )
    assert result == {"tier": "sonnet", "reason": "jev", "changed": True}


def test_decide_clamps_to_available_tiers():
    result = decide(
        prompt="fix this",
        jev={"choice": "fable", "confidence": 0.9},
        current="opus",
        available=["haiku", "sonnet", "opus"],
    )
    assert result["tier"] == "opus"
    assert result["reason"] == "jev+unavailable/no-change"
