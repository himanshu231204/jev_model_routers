"""Default configuration mirror of configs/default.yaml (stdlib only, no yaml dep)."""
DEFAULTS = {"router": {"enabled": True, "policy": "default", "fail_mode": "open"},
            "jev": {"timeout_ms": 1500, "deadline_ms": 3000, "max_retries": 1, "client": "stdlib"},
            "models": {"allow": ["anthropic/claude-fable", "anthropic/claude-haiku",
                                "anthropic/claude-sonnet", "anthropic/claude-opus",
                                "openai/coding-strong"]},
            "agents": {"auto_detect": True},
            "privacy": {"send_repository_content": False, "log_prompts": False},
            "routing": {"min_confidence": 0.30, "max_jev_latency_ms": 1500}}
