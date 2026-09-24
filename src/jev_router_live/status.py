"""Per-session routing decision file, read by the status line and ``jev-explain``."""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

# One file per session rather than a shared map, so concurrent sessions can never clobber
# each other's status. Kept in the temp dir so the OS eventually cleans up.
STATUS_DIR = Path(tempfile.gettempdir()) / "jev-claude"

# Status files hold prompt text and exact Jev exchanges, so only the owner may read them.
DIR_MODE = 0o700
FILE_MODE = 0o600

# Files not updated for this long belong to finished sessions and are removed.
STALE_AFTER_MS = 7 * 24 * 60 * 60 * 1000
_pruned = False

_SAFE_ID = re.compile(r"[^\w-]")


def _file_for(session_id: str) -> Path:
    return STATUS_DIR / f"{_SAFE_ID.sub('', session_id)}.json"


def _ensure_dir() -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True, mode=DIR_MODE)
    try:
        os.chmod(STATUS_DIR, DIR_MODE)
    except OSError:
        pass  # Another user owns the directory; the write below will fail too.


def write_status(session_id: str | None, status: dict) -> None:
    """Publish the latest routing decision so the status line can display it."""
    global _pruned
    if not session_id:
        return
    try:
        _ensure_dir()
        file = _file_for(session_id)
        file.write_text(json.dumps(status), encoding="utf-8")
        os.chmod(file, FILE_MODE)
        if not _pruned:
            _pruned = True
            prune_stale()
    except OSError:
        pass  # Status display is cosmetic and must never interfere with a request.


def write_decision(session_id: str | None, decision: dict) -> None:
    """Publish a routed prompt and retain recent exact Jev exchanges for diagnosis."""
    previous = read_status(session_id)
    history = [*((previous or {}).get("history") or []), decision][-20:]
    write_status(session_id, {**decision, "history": history})


def read_status(session_id: str | None) -> dict | None:
    """Latest routing decision for a session, or None if none has been made yet."""
    if not session_id:
        return None
    try:
        return json.loads(_file_for(session_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def prune_stale(max_age_ms: int = STALE_AFTER_MS, now: float | None = None) -> int:
    """Delete status files untouched for ``max_age_ms``. Runs once per process on first write."""
    now_ms = (now if now is not None else time.time() * 1000)
    removed = 0
    try:
        entries = list(STATUS_DIR.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if entry.suffix != ".json":
            continue
        try:
            mtime_ms = entry.stat().st_mtime * 1000
            if now_ms - mtime_ms > max_age_ms:
                entry.unlink()
                removed += 1
        except OSError:
            pass  # Another session may have removed or replaced it; ignore.
    return removed
