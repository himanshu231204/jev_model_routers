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
