"""File-based logging that never corrupts an interactive CLI's own terminal UI."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path.home() / ".jev-claude.log"

# The agent CLI owns the terminal in interactive mode and redraws over anything we print, so
# writing to stderr there corrupts its UI. Log to a file instead and leave stderr alone. In
# print/non-interactive mode there is no TUI to damage, so stderr stays convenient for piping.
_interactive = sys.stdout.isatty()


def log(line: str) -> None:
    text = f"[jev] {line}\n"
    if not _interactive:
        sys.stderr.write(text)
        return
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {text}")
    except OSError:
        pass  # A broken log file must never take down the session.


def debug(line: str) -> None:
    if os.environ.get("JEV_DEBUG"):
        log(line)
