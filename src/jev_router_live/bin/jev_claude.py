#!/usr/bin/env python3
"""Launches the real Claude Code CLI with the local per-turn routing proxy in front of it."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jev_router_live.config import AUTO_MODEL
from jev_router_live.env_file import load_env
from jev_router_live.log import LOG_FILE
from jev_router_live.proxy import start_proxy
from jev_router_live.settings import read_saved_model, restore_saved_model
from jev_router_live.status import private_dir


def _auto_model_env() -> dict[str, str]:
    """Registers "JEV Router" as an extra row in Claude Code's /model picker and starts the
    session on it. Claude Code sends the id verbatim because it does not validate model
    names behind a custom base URL, which is what lets the proxy tell "route this" from "the
    user picked a model". Capabilities are declared so Claude Code still composes thinking
    and effort for the tiers that support them; the proxy strips what the routed model
    cannot accept."""
    env = {
        "ANTHROPIC_CUSTOM_MODEL_OPTION": AUTO_MODEL,
        "ANTHROPIC_CUSTOM_MODEL_OPTION_NAME": "JEV Router",
        "ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION": "Route each turn to the cheapest model that can do it",
        "ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES": (
            "thinking,adaptive_thinking,interleaved_thinking,effort,max_effort"
        ),
        # Some Claude Code versions validate the model client-side before it reaches the
        # proxy; this defers to the API so "jev-router" can pass through for rewriting.
        # 2.1.281 still prints a one-line [claude-code:unrecognized_model] warning for the
        # sentinel -- advisory only (telemetry, deduped); the request is routed regardless.
        "CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT": "1",
    }
    # ANTHROPIC_MODEL applies to this session only and is never written to settings, so the
    # default costs the user nothing permanent. A model they set themselves still wins.
    if "ANTHROPIC_MODEL" not in os.environ:
        env["ANTHROPIC_MODEL"] = AUTO_MODEL
    return env


def _statusline_settings() -> Path | None:
    """Claude Code's UI shows the model it asked for, never the one the proxy routed to, so a
    status line is the only way to surface the decision. ``--settings`` merges rather than
    replaces, but a status line the user configured themselves still takes priority: theirs
    is a deliberate choice and silently overwriting it would be worse than showing nothing.

    Returns a settings file to pass with ``--settings`` (the caller deletes it on exit), or
    None. Claude Code executes the command in this file, so it is created with a unique name,
    owner-only, inside a directory verified to be private -- never at a fixed shared path."""
    if os.environ.get("JEV_NO_STATUSLINE"):
        return None
    for directory in (Path.cwd() / ".claude", Path.home() / ".claude"):
        try:
            if json.loads((directory / "settings.json").read_text(encoding="utf-8")).get("statusLine"):
                return None
        except (OSError, ValueError):
            pass  # No settings file, or unreadable; nothing to preserve.

    directory = private_dir()
    if directory is None:
        return None
    command = f'"{sys.executable}" -m jev_router_live.bin.jev_statusline'
    try:
        fd, name = tempfile.mkstemp(prefix="settings-", suffix=".json", dir=directory)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"statusLine": {"type": "command", "command": command}}, fh)
    except OSError:
        return None
    return Path(name)


def _resolve_claude() -> str | None:
    return shutil.which("claude")


def main() -> None:
    load_env()

    args = sys.argv[1:]
    env = dict(os.environ)

    claude = _resolve_claude()
    if not claude:
        sys.stderr.write(
            "[jev] Claude Code is not installed, or `claude` is not on your PATH.\n"
            "[jev] jev-claude runs the real Claude Code CLI; install it first:\n"
            "[jev]   https://code.claude.com/docs/en/setup\n"
        )
        sys.exit(1)

    close = lambda: None  # noqa: E731
    settings_file: Path | None = None
    saved_model_before = read_saved_model()

    if os.environ.get("JEV_API_KEY"):
        handle = start_proxy()
        close = handle.close
        env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{handle.port}"
        env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"
        env.update(_auto_model_env())
        settings_file = _statusline_settings()
        if settings_file:
            args += ["--settings", str(settings_file)]
        if os.environ.get("JEV_DEBUG") and sys.stdout.isatty():
            sys.stderr.write(f"[jev] routing decisions -> {LOG_FILE}\n")
    else:
        sys.stderr.write(
            "[jev] no JEV_API_KEY found - starting Claude Code without routing\n"
            f"[jev] add JEV_API_KEY=... to {Path.home() / '.jev-router.env'} to enable routing\n"
        )

    try:
        result = subprocess.run([claude, *args], env=env)
        code = result.returncode
    except OSError as exc:
        sys.stderr.write(f"[jev] could not start Claude Code: {exc}\n")
        code = 1
    finally:
        close()
        restore_saved_model(saved_model_before)
        if settings_file:
            settings_file.unlink(missing_ok=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
