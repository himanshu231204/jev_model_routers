"""Live-proxy routing dispatcher: stdlib HTTP by default, SDK when JEV_CLIENT=sdk.

``proxy.py`` and ``codex_proxy.py`` import ``ask_jev`` from this module; the name and
signature are unchanged. The stdlib implementation moved verbatim to
``stdlib_router.stdlib_ask_jev``; the best-effort SDK path lives in
``sdk_router.sdk_ask_jev``.
"""
from __future__ import annotations


def ask_jev(*, prompt, current, context_tokens, models):
    import os
    if os.environ.get("JEV_CLIENT") == "sdk":
        from jev_router_live.sdk_router import sdk_ask_jev
        return sdk_ask_jev(prompt=prompt, current=current, context_tokens=context_tokens, models=models)
    from jev_router_live.stdlib_router import stdlib_ask_jev
    return stdlib_ask_jev(prompt=prompt, current=current, context_tokens=context_tokens, models=models)
