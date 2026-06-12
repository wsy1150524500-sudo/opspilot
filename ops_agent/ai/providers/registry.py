from __future__ import annotations

from ops_agent.ai.errors import UnknownProviderError
from ops_agent.ai.models import ProviderConfig
from ops_agent.ai.providers.base import LLMProvider


class ProviderRegistry:
    _registry: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, key: str, provider_cls: type[LLMProvider]) -> None:
        cls._registry[key] = provider_cls

    @classmethod
    def create(cls, config: ProviderConfig) -> LLMProvider:
        key = config.kind.value
        provider_cls = cls._registry.get(key)
        if provider_cls is None:
            raise UnknownProviderError(
                f"Provider '{key}' is not registered. "
                f"Available: {list(cls._registry.keys())}"
            )
        return provider_cls(config)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._registry.clear()
