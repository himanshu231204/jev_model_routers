from jev_router.jev.schema import JEVDecision
from jev_router.jev.client import JevClient
from jev_router.jev.base import resolve_client_kind
__all__ = ["JEVDecision", "JevClient", "resolve_client_kind"]
def get_jev_client(config=None, **kw):
    import os
    kind = resolve_client_kind((config or {}), os.environ)
    if kind == "sdk":
        try:
            from jev_router.jev.sdk_client import SdkJevClient
            return SdkJevClient(**kw)
        except ImportError:
            return JevClient(**kw)
    return JevClient(**kw)
