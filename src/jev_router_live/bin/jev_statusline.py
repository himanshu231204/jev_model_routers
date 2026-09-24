#!/usr/bin/env python3
"""Port of jev-router's ``bin/jev-statusline.mjs``.

Status line for Claude Code. Claude Code pipes session JSON on stdin and renders whatever
this prints. See https://code.claude.com/docs/en/statusline
"""
from __future__ import annotations

import json
import sys

from jev_router_live.status import read_status

DIM = "\x1b[2m"
RESET = "\x1b[0m"
COLOR = {"haiku": "\x1b[32m", "sonnet": "\x1b[36m", "opus": "\x1b[35m", "fable": "\x1b[33m"}


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        data = {}

    status = read_status(data.get("session_id"))
    workspace = data.get("workspace") or {}
    dir_path = workspace.get("current_dir") or data.get("cwd") or ""
    directory = dir_path.replace("\\", "/").rstrip("/").split("/")[-1] if dir_path else ""
    pct = round((data.get("context_window") or {}).get("used_percentage", 0))

    routed = f"{DIM}jev: waiting for first prompt{RESET}"
    if status and status.get("manual"):
        model_display = (data.get("model") or {}).get("display_name", "")
        routed = f"{DIM}⏸ manual{RESET} {model_display}".rstrip()
    elif status:
        color = COLOR.get(status.get("tier"), "")
        confidence = status.get("confidence")
        p = f" {DIM}(p={confidence:.2f}){RESET}" if confidence is not None else ""
        reason = status.get("reason") or ""
        held = reason and reason not in ("jev", "jev/no-change") and "override" not in reason
        why = f" {DIM}({reason.split('/')[0]}){RESET}" if held else ""
        routed = f"{color}{status.get('model') or status.get('tier')}{RESET}{p}{why}"

    sys.stdout.write(f"{routed} {DIM}·{RESET} {directory} {DIM}· {pct}% context{RESET}\n")


if __name__ == "__main__":
    main()
