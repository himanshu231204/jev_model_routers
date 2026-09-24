import json, pathlib
from jev_router.adapters.claude_code.adapter import ClaudeCodeAdapter

def _load(name):
    return json.loads(pathlib.Path(f"tests/fixtures/claude_code/{name}").read_text())

def test_normalize_simple_turn():
    a = ClaudeCodeAdapter()
    n = a.normalize_request(_load("simple_turn.json"))
    assert n.agent == "claude_code" and n.prompt and n.session_id

def test_tool_loop_not_new_turn():
    a = ClaudeCodeAdapter()
    assert a.is_new_turn(_load("tool_loop.json")) is False

def test_apply_model_rewrites():
    a = ClaudeCodeAdapter()
    out = a.apply_model(_load("simple_turn.json"), "claude-opus")
    assert "claude-opus" in str(out)

def test_launch_command():
    a = ClaudeCodeAdapter()
    assert a.launch_command("claude-opus") == ["claude", "--model", "claude-opus"]

def test_launch_command_translates_catalog_ids_to_real_aliases():
    a = ClaudeCodeAdapter()
    assert a.launch_command("anthropic/claude-sonnet") == ["claude", "--model", "sonnet"]
    assert a.launch_command("anthropic/claude-opus") == ["claude", "--model", "opus"]
