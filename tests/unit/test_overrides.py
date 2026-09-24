from jev_router.core.overrides import detect_override

def test_use_opus_detected():
    o = detect_override("use opus for this", None)
    assert o is not None and o.value == "strong"

def test_no_override():
    assert detect_override("rename this variable", None) is None

def test_native_model_wins():
    o = detect_override("hello", "anthropic/claude-opus")
    assert o is not None and o.kind == "exact_model"
