"""Layered config: CLI args > env vars > project config > user config > defaults."""
from __future__ import annotations
import copy, json, os
from pathlib import Path
from jev_router.config.defaults import DEFAULTS
from jev_router.config.schema import validate

def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def _read_json_yaml(path: str | None) -> dict:
    if not path or not Path(path).exists():
        return {}
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}

def load(cli_args: dict | None = None, env: dict | None = None,
         project_path: str | None = None, user_path: str | None = None) -> dict:
    env = env if env is not None else os.environ
    cfg = copy.deepcopy(DEFAULTS)
    cfg = _deep_merge(cfg, _read_json_yaml(user_path))
    cfg = _deep_merge(cfg, _read_json_yaml(project_path))
    if env.get("JEV_ROUTER_POLICY"):
        cfg["router"]["policy"] = env["JEV_ROUTER_POLICY"]
    if env.get("JEV_TIMEOUT_MS"):
        cfg["jev"]["timeout_ms"] = int(env["JEV_TIMEOUT_MS"])
    for k, v in (cli_args or {}).items():
        head, _, tail = k.partition(".")
        if head in cfg and isinstance(cfg[head], dict):
            cfg[head][tail] = v
        else:
            cfg[k] = v
    return validate(cfg)
