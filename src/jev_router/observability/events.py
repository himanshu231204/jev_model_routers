"""Emits structured routing events such as routing.decision."""
from __future__ import annotations
from jev_router.contracts.events import RoutingEvent
def build_event(request_id, agent, session_id, turn_id, current, selected, conf, reason, latency_ms, fallback) -> RoutingEvent:
    return RoutingEvent(event="routing.decision", request_id=request_id, agent=agent, session_id=session_id,
                        turn_id=turn_id, current_model=current, selected_model=selected,
                        confidence=conf, reason=reason, jev_latency_ms=latency_ms, fallback=fallback)
