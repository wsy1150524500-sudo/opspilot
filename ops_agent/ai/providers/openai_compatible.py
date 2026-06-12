from __future__ import annotations

from ops_agent.ai.models import ProviderConfig
from ops_agent.ai.providers.openai_provider import OpenAIProvider
from ops_agent.ai.providers.registry import ProviderRegistry


class OpenAICompatibleProvider(OpenAIProvider):
    """Reuses the OpenAI SDK with a custom base_url.

    Covers DeepSeek, Alibaba Qwen/DashScope, Zhipu GLM, Moonshot Kimi, etc.
    """

    def __init__(self, config: ProviderConfig) -> None:
        if not config.base_url:
            from ops_agent.ai.errors import ConfigError

            raise ConfigError(
                "base_url is required for openai_compatible providers"
            )
        super().__init__(config)


# Register at import time
ProviderRegistry.register("openai_compatible", OpenAICompatibleProvider)
