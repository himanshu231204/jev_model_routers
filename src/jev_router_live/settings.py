"""Port of jev-router's ``src/settings.mjs``."""
from __future__ import annotations

import json
from pathlib import Path

from jev_router_live.config import AUTO_MODEL

USER_SETTINGS = Path.home() / ".claude" / "settings.json"


def read_saved_model(file: Path = USER_SETTINGS) -> str | None:
    """The model saved as the user's default, ignoring a sentinel left by a session that did
    not exit cleanly, which is not a preference worth restoring."""
    try:
        model = json.loads(file.read_text(encoding="utf-8")).get("model")
    except (OSError, ValueError):
        return None
    return None if model == AUTO_MODEL else model


def restore_saved_model(previous: str | None, file: Path = USER_SETTINGS) -> bool:
    """Puts ``previous`` back if the settings file now holds the sentinel. Selecting a row
    with Enter makes the CLI save it as the default for new sessions, and a saved
    "jev-router" would break a plain run of the CLI, which has no proxy to resolve it.
    Anything other than an exact sentinel match is left alone, so a real model chosen during
    the session survives."""
    try:
        settings = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if settings.get("model") != AUTO_MODEL:
        return False
    if previous is None:
        settings.pop("model", None)
    else:
        settings["model"] = previous
    try:
        file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True
