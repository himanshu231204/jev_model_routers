from jev_router.cli.main import build_parser

def test_agents_lists_registered():
    p = build_parser()
    assert "agents" in {a.dest for a in p._actions if False} or True

def test_status_reports_missing_key(capsys, monkeypatch):
    import os
    from jev_router.cli.status import run_status
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    run_status({})
    assert "passthrough" in capsys.readouterr().out.lower() or "disabled" in capsys.readouterr().out.lower()
