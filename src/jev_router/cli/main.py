"""Console entry point for the jev-router CLI: parses arguments and dispatches subcommands."""
from __future__ import annotations
import argparse
from jev_router.cli.run import run_run
from jev_router.cli.agents import run_agents
from jev_router.cli.models import run_models
from jev_router.cli.status import run_status
from jev_router.cli.explain import run_explain
from jev_router.cli.doctor import run_doctor

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jev-router")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("run"); r.add_argument("--agent", default="claude_code")
    sub.add_parser("agents"); sub.add_parser("models"); sub.add_parser("status"); sub.add_parser("doctor")
    e = sub.add_parser("explain"); e.add_argument("--agent", default=""); e.add_argument("--session", default=""); e.add_argument("--turn", default="")
    return p

def main(argv=None) -> int:
    args = vars(build_parser().parse_args(argv))
    cmd = args.pop("cmd", None) or "status"
    return {"run": run_run, "agents": run_agents, "models": run_models,
            "status": run_status, "explain": run_explain, "doctor": run_doctor}[cmd](args)
