"""Per-turn live model router for Claude Code and OpenAI Codex.

A local HTTP proxy in front of the agent's own API routes every fresh user
turn to the cheapest model tier that can do the work, via TypeSafe's Jev
(System One) API.

Entry points: ``jev-claude`` and ``jev-codex`` wrap the real CLIs; use
``jev-explain`` (or the bundled skill) to see why the last turn was routed
the way it was.
"""

from jev_router_live.version import __version__

__all__ = ["__version__"]
