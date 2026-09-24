from jev_router_live.config import (
    AUTO_MODEL,
    TIER_NAMES,
    id_of,
    is_auto,
    rank_of,
    should_use_exact_model,
    tier_of,
)


def test_tier_of_matches_family_substring():
    assert tier_of("claude-sonnet-4-6") == "sonnet"
    assert tier_of("claude-opus-5") == "opus"
    assert tier_of("gpt-4") is None
    assert tier_of(None) is None


def test_is_auto():
    assert is_auto(AUTO_MODEL) is True
    assert is_auto("claude-opus-5") is False


def test_rank_and_id_are_consistent():
    assert rank_of("haiku") < rank_of("sonnet") < rank_of("opus") < rank_of("fable")
    for name in TIER_NAMES:
        assert id_of(name) is not None


def test_should_use_exact_model():
    assert should_use_exact_model("jev", "sonnet", "sonnet") is True
    assert should_use_exact_model("jev/no-change", "sonnet", "sonnet") is True
    assert should_use_exact_model("override", "sonnet", "sonnet") is False
    assert should_use_exact_model("jev", "haiku", "sonnet") is False
