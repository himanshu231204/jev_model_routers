"""CLI command that launches a coding agent with a JEV-routed model for the session."""
from __future__ import annotations
import subprocess
from jev_router.adapters.registry import get_adapter
from jev_router.config.loader import load
from jev_router.contracts.models import ModelSpec
from jev_router.contracts.requests import NormalizedRequest
from jev_router.core.router import Router
from jev_router.jev.client import JevClient
from jev_router.state.memory import MemoryStore


def _candidates(cfg: dict) -> list[ModelSpec]:
    return [ModelSpec(id=m, provider=m.split("/", 1)[0]) for m in cfg["models"]["allow"]]


def run_run(args: dict) -> int:
    name = args.get("agent", "claude_code")
    adapter = get_adapter(name)
    cfg = load()
    jev = JevClient(timeout_ms=cfg["jev"]["timeout_ms"], deadline_ms=cfg["jev"]["deadline_ms"],
                     max_retries=cfg["jev"]["max_retries"])
    router = Router(jev_client=jev, store=MemoryStore(), candidates=_candidates(cfg), privacy=cfg["privacy"])
    request = NormalizedRequest(request_id="cli_run", agent=name, session_id="cli-session",
                                conversation_id="cli-session", turn_id="t1", prompt="",
                                available_models=cfg["models"]["allow"])
    decision = router.route(request)
    print(f"routing: agent={name} model={decision.final_model} reason={decision.reason}")
    try:
        cmd = adapter.launch_command(decision.final_model)
    except NotImplementedError as e:
        print(f"error: {e}")
        return 1
    return subprocess.run(cmd).returncode
