"""Agent identity and capability contract shared across adapters."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AgentCapabilities:
    supports_proxy: bool = False
    supports_custom_base_url: bool = False
    supports_custom_provider: bool = False
    supports_model_override: bool = True
    supports_streaming_intercept: bool = False
    supports_sdk_middleware: bool = False
    supports_native_status_display: bool = False
    supports_subagent_identification: bool = False
