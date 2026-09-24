import json, pathlib
from jev_router.adapters.registry import get_adapter, registered

def _load(agent):
    return json.loads(pathlib.Path(f"tests/fixtures/{agent}/simple_turn.json").read_text())

def test_all_registered():
    assert {"claude_code", "codex", "opencode", "hermes", "deepagents"} <= set(registered())

def test_contract_codex():
    a = get_adapter("codex")
    n = a.normalize_request(_load("codex"))
    assert n.agent == "codex" and n.prompt
    assert "test-model" in str(a.apply_model(_load("codex"), "test-model"))

def test_contract_opencode_hermes_deepagents():
    for name in ("opencode", "hermes", "deepagents"):
        a = get_adapter(name)
        n = a.normalize_request(_load(name))
        assert n.session_id and n.prompt
        assert "m-strong" in str(a.apply_model(_load(name), "m-strong"))

def test_launch_command_cli_agents():
    assert get_adapter("codex").launch_command("m") == ["codex", "--model", "m"]
    assert get_adapter("hermes").launch_command("m") == ["hermes", "chat", "--model", "m"]

def test_launch_command_deepagents_not_implemented():
    import pytest
    with pytest.raises(NotImplementedError):
        get_adapter("deepagents").launch_command("m")

def test_launch_command_opencode_not_implemented():
    import pytest
    with pytest.raises(NotImplementedError):
        get_adapter("opencode").launch_command("m")

def test_hermes_detect_uses_shutil_which(monkeypatch):
    import shutil
    from jev_router.adapters.hermes.adapter import HermesAdapter
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/hermes" if name == "hermes" else None)
    assert HermesAdapter().detect() is True
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert HermesAdapter().detect() is False
