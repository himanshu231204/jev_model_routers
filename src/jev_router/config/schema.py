"""Config validation for router settings."""
_ALLOWED_POLICIES = {"default", "cost-first", "latency-first", "quality-first", "conservative"}

def validate(config: dict) -> dict:
    pol = config.get("router", {}).get("policy", "default")
    if pol not in _ALLOWED_POLICIES:
        raise ValueError(f"unknown policy: {pol}")
    for k in ("timeout_ms", "deadline_ms"):
        v = config.get("jev", {}).get(k)
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise ValueError(f"jev.{k} must be positive int")
    return config
