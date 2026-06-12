from __future__ import annotations

from functools import lru_cache

from ops_agent.core.config import load_config
from ops_agent.core.models import AppConfig
from ops_agent.services.log_service import LogService
from ops_agent.services.ssh_service import SSHService
from ops_agent.services.system_service import SystemService


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return load_config()


def get_system_service() -> SystemService:
    return SystemService()


def get_log_service() -> LogService:
    return LogService()


def get_ssh_service() -> SSHService:
    return SSHService()


def get_agent_runner():
    """Build an AgentRunner from the AI config. Returns None if no config found."""
    import os

    from ops_agent.ai.agent import AgentRunner
    from ops_agent.ai.config import load_ai_config
    from ops_agent.ai.tools import build_default_registry

    # Lazy-import providers so they register
    import ops_agent.ai.providers.openai_provider  # noqa: F401
    import ops_agent.ai.providers.anthropic_provider  # noqa: F401
    import ops_agent.ai.providers.openai_compatible  # noqa: F401

    from ops_agent.ai.providers.registry import ProviderRegistry

    config_path = os.environ.get("OPS_AI_CONFIG", "config/ai.yaml")
    ai_config = load_ai_config(config_path)
    app_config = get_config()

    provider = ProviderRegistry.create(ai_config.provider)
    registry = build_default_registry(ai_config, app_config)
    return AgentRunner(
        provider=provider,
        registry=registry,
        max_iterations=ai_config.max_iterations,
        system_prompt=ai_config.system_prompt,
    )
