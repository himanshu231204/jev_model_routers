# tests/unit/test_config.py
from jev_router.config.loader import load
from jev_router.config.defaults import DEFAULTS

def test_precedence_cli_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_ROUTER_POLICY", "cost-first")
    cfg = load(cli_args={"router.policy": "quality-first"}, env=dict(JEV_ROUTER_POLICY="cost-first"),
               project_path=None, user_path=None)
    assert cfg["router"]["policy"] == "quality-first"
    assert cfg["jev"]["timeout_ms"] == 1500

def test_validate_rejects_bad_policy():
    from jev_router.config.schema import validate
    try:
        validate({"router": {"policy": "nope"}})
    except ValueError:
        return
    raise AssertionError("should have raised")

def test_config_accepts_jev_client_kind():
    from jev_router.config.loader import load
    cfg = load(cli_args={}, env={}, project_path=None, user_path=None)
    assert cfg["jev"]["client"] == "stdlib"
    cfg2 = load(cli_args={}, env={"JEV_CLIENT": "sdk"}, project_path=None, user_path=None)
    assert cfg2["jev"]["client"] == "sdk"
