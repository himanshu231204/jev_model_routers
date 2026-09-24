"""Registry of model providers available to the router."""
from __future__ import annotations
from jev_router.providers.anthropic import AnthropicProvider
from jev_router.providers.openai import OpenAIProvider
from jev_router.providers.google import GoogleProvider
from jev_router.providers.openrouter import OpenRouterProvider
from jev_router.providers.ollama import OllamaProvider
from jev_router.providers.custom import CustomProvider
PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAIProvider, "google": GoogleProvider,
             "openrouter": OpenRouterProvider, "ollama": OllamaProvider, "custom": CustomProvider}
def get_provider(name: str):
    return PROVIDERS[name]()
