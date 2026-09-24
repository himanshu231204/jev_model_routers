"""Minimal ``.env``-style loader (Node's ``process.loadEnvFile`` has no stdlib Python
equivalent). Existing environment variables always win."""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env(cwd: Path | None = None, home: Path | None = None) -> None:
    """Project-local, then shared user-level, then the legacy Claude-specific file."""
    cwd = cwd or Path.cwd()
    home = home or Path.home()
    for candidate in (cwd / ".env", home / ".jev-router.env", home / ".jev-claude.env"):
        load_env_file(candidate)
