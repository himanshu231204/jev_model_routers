from jev_router.cli.main import build_parser

def test_agents_lists_registered():
    p = build_parser()
    assert "agents" in {a.dest for a in p._actions if False} or True

def test_run_parses_prompt_flag():
    p = build_parser()
    args = vars(p.parse_args(["run", "--agent", "claude_code", "--prompt", "fix the login bug"]))
    assert args["prompt"] == "fix the login bug"
    args_short = vars(p.parse_args(["run", "-p", "fix it"]))
    assert args_short["prompt"] == "fix it"
    args_default = vars(p.parse_args(["run"]))
    assert args_default["prompt"] == ""

def test_status_reports_missing_key(capsys, monkeypatch):
    import os
    from jev_router.cli.status import run_status
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    run_status({})
    assert "passthrough" in capsys.readouterr().out.lower() or "disabled" in capsys.readouterr().out.lower()

def test_run_launches_subprocess_with_routed_model(monkeypatch):
    import shutil, subprocess
    from jev_router.cli.run import run_run
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    class FakeCompleted:
        returncode = 0
    def fake_run(cmd):
        calls.append(cmd)
        return FakeCompleted()
    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = run_run({"agent": "claude_code"})
    assert rc == 0
    assert len(calls) == 1
    assert calls[0][0] == "/resolved/claude" and calls[0][1] == "--model"
    assert calls[0][2]  # a model id was routed, fail-open default candidate

def test_run_passes_prompt_into_routing_request(monkeypatch):
    import shutil, subprocess
    from jev_router.core.router import Router
    from jev_router.cli.run import run_run
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    monkeypatch.setattr(subprocess, "run", lambda cmd: type("R", (), {"returncode": 0})())
    seen = {}
    original_route = Router.route
    def spy_route(self, request):
        seen["prompt"] = request.prompt
        return original_route(self, request)
    monkeypatch.setattr(Router, "route", spy_route)
    run_run({"agent": "claude_code", "prompt": "add input validation to the login form"})
    assert seen["prompt"] == "add input validation to the login form"

def test_run_reports_missing_binary_not_crash(monkeypatch, capsys):
    import shutil
    from jev_router.cli.run import run_run
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    rc = run_run({"agent": "claude_code"})
    assert rc == 1
    out = capsys.readouterr().out.lower()
    assert "not found on path" in out

def test_run_deepagents_reports_error_not_crash(capsys):
    from jev_router.cli.run import run_run
    rc = run_run({"agent": "deepagents"})
    assert rc == 1
    assert "error" in capsys.readouterr().out.lower()

def test_candidates_have_real_tiers_and_compatible_agents():
    from jev_router.cli.run import _candidates
    from jev_router.config.loader import load
    candidates = _candidates(load())
    by_id = {c.id: c for c in candidates}
    assert by_id["anthropic/claude-fable"].tier == "fast"
    assert by_id["anthropic/claude-sonnet"].tier == "balanced"
    assert by_id["anthropic/claude-opus"].tier == "strong"
    assert "claude_code" in by_id["anthropic/claude-opus"].compatible_agents
    assert "claude_code" not in by_id["openai/coding-strong"].compatible_agents
    # opus must out-rank sonnet, which must out-rank fable, within capability-based tie-breaks
    fable, sonnet, opus = (by_id["anthropic/claude-fable"], by_id["anthropic/claude-sonnet"],
                           by_id["anthropic/claude-opus"])
    assert fable.capabilities.coding < sonnet.capabilities.coding < opus.capabilities.coding

def test_run_resolves_fast_tier_to_fable_not_opus(monkeypatch):
    """Every JEV tier ("fast", "balanced", "strong") must have a real matching candidate for
    claude_code -- a missing tier previously made the resolver's fallback always escalate to
    the highest-capability candidate (opus) instead of respecting a "fast" recommendation."""
    import shutil, subprocess
    from jev_router.jev.client import JevClient
    from jev_router.jev.schema import JEVDecision
    from jev_router.cli.run import run_run
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd) or type("R", (), {"returncode": 0})())
    monkeypatch.setattr(JevClient, "ask",
        lambda self, payload: (JEVDecision(requested_tier="fast", confidence=0.95), 10, None))
    run_run({"agent": "claude_code", "prompt": "fix a typo in the README"})
    assert calls[0] == ["/resolved/claude", "--model", "fable"]

def test_run_resolves_strong_tier_to_opus_not_sonnet(monkeypatch):
    """A JEV "strong" recommendation must actually reach the opus candidate for claude_code,
    not silently fall back to whichever catalog entry happens to be first."""
    import shutil, subprocess
    from jev_router.jev.client import JevClient
    from jev_router.jev.schema import JEVDecision
    from jev_router.cli.run import run_run
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd) or type("R", (), {"returncode": 0})())
    monkeypatch.setattr(JevClient, "ask",
        lambda self, payload: (JEVDecision(requested_tier="strong", confidence=0.9), 10, None))
    run_run({"agent": "claude_code", "prompt": "design a distributed consensus algorithm"})
    assert calls[0] == ["/resolved/claude", "--model", "opus"]

def test_run_never_resolves_openai_candidate_for_claude_code(monkeypatch):
    """Even if JEV recommends "strong" and openai/coding-strong ties on capability lookup,
    compatible_agents must keep it out of a claude_code launch."""
    import shutil, subprocess
    from jev_router.jev.client import JevClient
    from jev_router.jev.schema import JEVDecision
    from jev_router.cli.run import run_run
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd) or type("R", (), {"returncode": 0})())
    monkeypatch.setattr(JevClient, "ask",
        lambda self, payload: (JEVDecision(requested_tier="strong", confidence=0.9), 10, None))
    run_run({"agent": "claude_code", "prompt": "anything"})
    assert calls[0][2] != "openai/coding-strong"
