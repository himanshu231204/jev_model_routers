"""Tool-continuation pinning: opencode/hermes/deepagents must not re-route on tool results."""
from jev_router.adapters.opencode.adapter import OpenCodeAdapter
from jev_router.adapters.hermes.adapter import HermesAdapter
from jev_router.adapters.deepagents.adapter import DeepAgentsAdapter


def _check(adapter, fresh_extra=None):
    cont = {"session_id": "s", "prompt": "x", "model": "m",
            "available_models": ["m"], "tool_result": True}
    req = adapter.normalize_request(cont)
    assert req.is_new_turn is False
    assert req.metadata["tool_result"] is True
    assert adapter.is_new_turn(cont) is False
    fresh = {"session_id": "s", "prompt": "x", "model": "m",
             "available_models": ["m"], **(fresh_extra or {})}
    freq = adapter.normalize_request(fresh)
    assert freq.is_new_turn is True
    assert adapter.is_new_turn(fresh) is True


def test_opencode_tool_continuation():
    _check(OpenCodeAdapter())


def test_hermes_tool_continuation():
    _check(HermesAdapter())


def test_deepagents_tool_continuation():
    _check(DeepAgentsAdapter())
