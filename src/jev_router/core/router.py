"""Routing engine that turns a normalized fresh-turn request into a pinned model decision."""
from __future__ import annotations
from typing import Any
from jev_router.contracts.requests import NormalizedRequest
from jev_router.core.decision import RoutingDecision

class Router:
    def __init__(self, jev_client: Any, store: Any, candidates: list | None = None,
                 policy: Any = None, resolver: Any = None, privacy: dict | None = None):
        from jev_router.core.policy import Policy
        from jev_router.core.resolver import ModelResolver
        self.jev = jev_client
        self.store = store
        self.candidates = candidates or []
        self.policy = policy or Policy()
        self.resolver = resolver or ModelResolver()
        self.privacy = privacy or {}

    def _no_candidates_fallback(self, request: NormalizedRequest) -> RoutingDecision:
        # Fail-open: resolver raises ValueError only when candidates are empty
        # and no current model exists; never propagate a traceback to the caller.
        return RoutingDecision(final_model=request.current_model or "", reason="no_candidates",
                               changed=False, fallback=True, confidence=0.0,
                               pinned_until=request.turn_id)

    def route(self, request: NormalizedRequest) -> RoutingDecision:
        from jev_router.core.classifier import RequestKind, classify
        from jev_router.core.lifecycle import TurnState, state_key
        from jev_router.core.overrides import detect_override
        from jev_router.jev.questions import build_jev_payload
        key = state_key(request.agent, request.session_id, request.conversation_id,
                        (request.metadata or {}).get("subagent_id") if request.is_subagent else None)
        kind = classify(request)
        if kind in (RequestKind.TOOL_CONTINUATION, RequestKind.AUXILIARY):
            pinned = self.store.get(key)
            if pinned:
                return RoutingDecision(final_model=pinned.model, reason="pinned_reuse",
                                       changed=False, fallback=False, confidence=pinned.confidence, pinned_until=pinned.turn_id)
            return RoutingDecision(final_model=request.current_model or "", reason="no_pin_passthrough",
                                   changed=False, fallback=True, confidence=0.0)
        override = detect_override(request.prompt, (request.metadata or {}).get("native_model"))
        if override is not None:
            pol = self.policy.evaluate(request, None, override)
            try:
                res = self.resolver.resolve(request, pol, self.candidates)
            except ValueError:
                return self._no_candidates_fallback(request)
            self.store.pin(key, TurnState(turn_id=request.turn_id, model=res.model,
                                          tier=pol.tier or "balanced", reason=pol.reason, confidence=1.0))
            return RoutingDecision(final_model=res.model, reason=pol.reason,
                                   changed=(res.model != request.current_model), fallback=res.fallback, confidence=1.0, pinned_until=request.turn_id)
        payload = build_jev_payload(request, self.privacy)
        decision, latency_ms, error = self.jev.ask(payload)
        jev_dict = None
        if decision is not None:
            jev_dict = {"requested_model": decision.requested_model, "requested_tier": decision.requested_tier, "confidence": decision.confidence}
        pol = self.policy.evaluate(request, jev_dict, None)
        try:
            res = self.resolver.resolve(request, pol, self.candidates)
        except ValueError:
            return self._no_candidates_fallback(request)
        fell_back = pol.fallback or res.fallback or error is not None
        reason = pol.reason if error is None else f"jev_fallback:{error}"
        self.store.pin(key, TurnState(turn_id=request.turn_id, model=res.model,
                                      tier=pol.tier or "balanced", reason=reason, confidence=pol.confidence))
        return RoutingDecision(final_model=res.model, reason=reason,
                               changed=(res.model != request.current_model), fallback=fell_back,
                               confidence=pol.confidence, pinned_until=request.turn_id)
