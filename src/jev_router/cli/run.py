"""CLI command that launches a coding agent with a JEV-routed model for the session."""
from __future__ import annotations
import shutil, subprocess
from jev_router.adapters.registry import get_adapter
from jev_router.config.loader import load
from jev_router.contracts.models import ModelCapabilities, ModelSpec
from jev_router.contracts.requests import NormalizedRequest
from jev_router.core.router import Router
from jev_router.jev import get_jev_client
from jev_router.state.memory import MemoryStore

# Tier/capability/compatible-agent metadata for the ids shipped in configs/default.yaml's
# models.allow. Without this, ModelSpec's dataclass defaults (tier="balanced", identical
# ModelCapabilities(), empty compatible_agents) make every catalog entry look the same to
# ModelResolver: a JEV "strong" recommendation can never match any candidate's tier, and any
# candidate is "compatible" with any agent -- including an openai/* id "winning" a claude_code
# launch, which would then fail. Ids not listed here fall back to those same lenient defaults
# (unknown to the router, so nothing is asserted about them) rather than being rejected.
_KNOWN_MODELS = {
    "anthropic/claude-fable": {
        "tier": "fast", "compatible_agents": ["claude_code", "opencode", "hermes"],
        "capabilities": ModelCapabilities(coding=4, reasoning=4, speed=9, cost=9),
    },
    "anthropic/claude-haiku": {
        "tier": "fast", "compatible_agents": ["claude_code", "opencode", "hermes"],
        "capabilities": ModelCapabilities(coding=4, reasoning=4, speed=9, cost=9),
    },
    "anthropic/claude-sonnet": {
        "tier": "balanced", "compatible_agents": ["claude_code", "opencode", "hermes"],
        "capabilities": ModelCapabilities(coding=7, reasoning=7),
    },
    "anthropic/claude-opus": {
        "tier": "strong", "compatible_agents": ["claude_code", "opencode", "hermes"],
        "capabilities": ModelCapabilities(coding=9, reasoning=9),
    },
    "openai/coding-strong": {
        "tier": "strong", "compatible_agents": ["codex", "opencode", "hermes"],
        "capabilities": ModelCapabilities(coding=8, reasoning=8),
    },
}


def _candidates(cfg: dict) -> list[ModelSpec]:
    out = []
    for m in cfg["models"]["allow"]:
        meta = _KNOWN_MODELS.get(m, {})
        out.append(ModelSpec(id=m, provider=m.split("/", 1)[0], tier=meta.get("tier", "balanced"),
                             compatible_agents=meta.get("compatible_agents", []),
                             capabilities=meta.get("capabilities", ModelCapabilities())))
    return out


def run_run(args: dict) -> int:
    name = args.get("agent", "claude_code")
    adapter = get_adapter(name)
    cfg = load()
    jev = get_jev_client(cfg, timeout_ms=cfg["jev"]["timeout_ms"], deadline_ms=cfg["jev"]["deadline_ms"],
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
