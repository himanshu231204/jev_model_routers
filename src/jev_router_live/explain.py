"""Port of jev-router's ``src/explain.mjs``."""
from __future__ import annotations

from typing import Any

_WIDTH = 33


def _row(text: str = "") -> str:
    return f"│ {text[: _WIDTH - 2].ljust(_WIDTH - 2)} │"


def _metric(value: float | None) -> str:
    return f"{value:.2f}" if isinstance(value, (int, float)) else "n/a"


def _wrapped(label: str, value: str) -> list[str]:
    words = " ".join(f"{label}{value}".split()).split(" ")
    lines: list[str] = []
    for word in words:
        if not lines or len(f"{lines[-1]} {word}") > _WIDTH - 2:
            lines.append(word)
        else:
            lines[-1] += f" {word}"
    return [_row(line) for line in lines]


def _decision(reason: str = "") -> str:
    if "override" in reason:
        return "prompt override"
    if "jev-unavailable" in reason:
        return "Jev unavailable; held"
    if "low-confidence-no-downgrade" in reason:
        return "low confidence; held"
    if "low-confidence-capped" in reason:
        return "low confidence; capped"
    if "cache-rebuild" in reason:
        return "cache rebuild avoided"
    if "unavailable" in reason:
        return "nearest available tier"
    return "Jev recommendation"


def format_explanation(status: dict[str, Any] | None) -> str:
    if not status:
        return "Jev Router: no routing decision has been recorded for this session."
    if status.get("manual"):
        return "Jev Router: routing is paused because you selected a model manually."

    metrics = status.get("metrics") or {}
    jev = status.get("jev") or {}
    request_state = ((jev.get("request") or {}).get("state")) or {}
    response_answers = ((jev.get("response") or {}).get("answers")) or {}
    recommendation = (
        (response_answers.get("model_tier") or {}).get("choice")
        or status.get("tier")
        or "unknown"
    )
    session = request_state.get("session") or {}
    confidence = status.get("confidence")

    lines = [
        f"┌{'─' * _WIDTH}┐",
        _row("Jev Router"),
        _row(),
        _row("Jev request"),
        *_wrapped("Prompt: ", status.get("prompt") or "not recorded"),
        _row(f"Current tier: {str(session.get('current_model') or 'unknown').upper()}"),
        _row(f"Context tokens: {session.get('context_tokens', 'unknown')}"),
        _row(),
        _row("Jev response"),
        _row(f"Task complexity     {_metric(metrics.get('taskComplexity'))}"),
        _row(f"Reasoning required  {_metric(metrics.get('reasoningRequired'))}"),
        _row(f"Tool complexity     {_metric(metrics.get('toolComplexity'))}"),
        _row(f"Context size        {_metric(metrics.get('contextSize'))}"),
        _row(),
        _row(f"Recommended tier: {str(recommendation).upper()}"),
        _row(f"Selected model: {str(status.get('model') or status.get('tier') or 'unknown').upper()}"),
        _row(),
        _row(f"Confidence: {'n/a' if confidence is None else f'{round(confidence * 100)}%'}"),
        _row(f"Decision: {_decision(status.get('reason') or '')}"),
        f"└{'─' * _WIDTH}┘",
    ]
    return "\n".join(lines)
