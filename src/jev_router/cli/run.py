"""CLI command that launches a coding agent with a JEV-routed model for the session."""
from __future__ import annotations
import shutil, subprocess
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
                                conversation_id="cli-session", turn_id="t1",
                                prompt=args.get("prompt", ""),
                                available_models=cfg["models"]["allow"])
    decision = router.route(request)
    print(f"routing: agent={name} model={decision.final_model} reason={decision.reason}")
    try:
        cmd = adapter.launch_command(decision.final_model)
    except NotImplementedError as e:
        print(f"error: {e}")
        return 1
    # shutil.which resolves the full path (e.g. claude.CMD on Windows) so subprocess.run's
    # CreateProcess can find it; a bare "claude" fails there even when it's on PATH.
    resolved = shutil.which(cmd[0])
    if resolved is None:
        print(f"error: '{cmd[0]}' not found on PATH — is it installed?")
        return 1
    try:
        return subprocess.run([resolved, *cmd[1:]]).returncode
    except OSError as e:
        print(f"error: failed to launch '{cmd[0]}': {e}")
        return 1
