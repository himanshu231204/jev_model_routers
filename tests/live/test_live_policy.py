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


def test_detect_override_aliases_need_an_explicit_mode_word():
    """Tier aliases (fast/balanced/strong/long) are ordinary English in coding prompts, so they
    only count as an override when phrased as a mode/model/tier or at the end of a clause;
    otherwise Jev would be silently bypassed (e.g. "use fast lookups" forcing Haiku)."""
    assert detect_override("switch to fast mode") == "haiku"
    assert detect_override("use the strong model") is None  # article: not the override phrase
    assert detect_override("use strong model for this") == "opus"
    assert detect_override("switch to balanced tier please") == "sonnet"
    assert detect_override("please switch to fast.") == "haiku"
    assert detect_override("switch to fast") == "haiku"
    assert detect_override("use sonnet to rename this") == "sonnet"  # model names need no suffix
    for prompt in [
        "Fix the crash with long filenames",
        "Implement this with balanced parentheses checking",
        "Refactor the parser with strong typing",
        "Switch the cache to use fast lookups",
        "Add retries on long-running jobs",
    ]:
        assert detect_override(prompt) is None, prompt


def test_decide_is_total_for_malformed_confidence():
    """A non-numeric or NaN confidence from Jev must not raise; it is treated as no confidence,
    so it can never downgrade."""
    for bad in [None, "0.9", True, float("nan"), [0.9]]:
        result = decide(
            prompt="fix this",
            jev={"choice": "haiku", "confidence": bad},
            current="opus",
            available=["haiku", "sonnet", "opus"],
        )
        assert result["tier"] == "opus", bad
        assert result["reason"] == "low-confidence-no-downgrade/no-change", bad
