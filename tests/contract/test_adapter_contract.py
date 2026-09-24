import pytest
from jev_router.adapters.registry import registered, get_adapter

@pytest.mark.parametrize("name", registered())
def test_adapter_contract(name):
    a = get_adapter(name)
    raw = {"session_id": "s", "prompt": "hi", "input_text": "hi", "model": "m1", "available_models": ["m1", "m2"]}
    n = a.normalize_request(raw)
    assert n.agent == a.name and n.prompt and n.session_id
    assert "m2" in str(a.apply_model(raw, "m2"))
