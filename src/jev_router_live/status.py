"""Per-session routing decision file, read by the status line and ``jev-explain``."""
from __future__ import annotations

import json
import os
import re
import stat
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


def private_dir() -> Path | None:
    """``STATUS_DIR``, created if needed, but only if it is a real directory owned by this
    user and closed to everyone else; otherwise None.

    On Linux the temp dir is the shared /tmp, so another local user could pre-create
    ``/tmp/jev-claude``. Writing prompts (or the Claude Code settings file) into a directory
    they own would let them read or replace it, so such a directory is never used."""
    try:
        STATUS_DIR.mkdir(parents=True, exist_ok=True, mode=DIR_MODE)
        st = os.lstat(STATUS_DIR)
        if not stat.S_ISDIR(st.st_mode):
            return None
        if hasattr(os, "getuid"):  # POSIX; Windows temp dirs are already per-user
            if st.st_uid != os.getuid():
                return None
            if stat.S_IMODE(st.st_mode) != DIR_MODE:
                os.chmod(STATUS_DIR, DIR_MODE)
    except OSError:
        return None
    return STATUS_DIR


def write_private(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` with owner-only permissions from the moment it exists."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, FILE_MODE)  # tighten files written by earlier versions too


def write_status(session_id: str | None, status: dict) -> None:
    """Publish the latest routing decision so the status line can display it."""
    global _pruned
    if not session_id or private_dir() is None:
        return
    try:
        write_private(_file_for(session_id), json.dumps(status))
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
    if not session_id or private_dir() is None:
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
