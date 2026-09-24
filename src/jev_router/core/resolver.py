"""Resolves a policy decision to a concrete model available to the selected agent and provider."""
from __future__ import annotations
from jev_router.contracts.requests import NormalizedRequest
from jev_router.contracts.models import ModelSpec
from jev_router.core.decision import PolicyDecision, ModelResolution

class ModelResolver:
    def resolve(self, request: NormalizedRequest, decision: PolicyDecision,
                candidates: list[ModelSpec]) -> ModelResolution:
        enabled = [c for c in candidates if c.enabled]
        if request.agent:
            agent_ok = [c for c in enabled if not c.compatible_agents or request.agent in c.compatible_agents]
            if agent_ok:
                enabled = agent_ok
        if request.available_models:
            avail = [c for c in enabled if c.id in request.available_models or c.id in request.available_models or any(a in request.available_models for a in c.aliases)]
            if avail:
                enabled = avail
        if decision.requested_model:
            for c in enabled:
                if c.id == decision.requested_model or decision.requested_model in c.aliases:
                    return ModelResolution(model=c.id, reason=decision.reason, fallback=False)
        if decision.tier:
            tiered = [c for c in enabled if c.tier == decision.tier]
            pool = tiered or enabled
            if pool:
                best = max(pool, key=lambda c: (c.capabilities.coding, c.capabilities.reasoning))
                return ModelResolution(model=best.id, reason=decision.reason, fallback=not bool(tiered))
        if request.current_model and any(c.id == request.current_model for c in candidates):
            return ModelResolution(model=request.current_model, reason="keep_current", fallback=True)
        if enabled:
            return ModelResolution(model=enabled[0].id, reason="default_candidate", fallback=True)
        if request.current_model:
            return ModelResolution(model=request.current_model, reason="no_candidates", fallback=True)
        raise ValueError("no model candidates and no current model")
