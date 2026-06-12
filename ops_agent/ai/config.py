from __future__ import annotations

import os
import stat
from pathlib import Path

import yaml

from ops_agent.ai.errors import ConfigError
from ops_agent.ai.models import AIConfig, ProviderConfig, ProviderKind
from ops_agent.core.config import _substitute_env


def load_ai_config(path: str | None = None) -> AIConfig:
    if path is None:
        raise ConfigError(
            "No AI config file specified. Run 'ops ai setup' to create one."
        )

    if not os.path.exists(path):
        raise ConfigError(f"AI config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError(f"AI config file is empty: {path}")

    raw = _substitute_env(raw)

    # Validate base_url for openai_compatible
    provider_raw = raw.get("provider", {})
    kind = provider_raw.get("kind")
    base_url = provider_raw.get("base_url")
    if kind == ProviderKind.OPENAI_COMPATIBLE.value and not base_url:
        raise ConfigError(
            "base_url is required for openai_compatible providers"
        )

    return AIConfig.model_validate(raw)


def save_ai_config(
    config: AIConfig, path: str, store_key_as_env: bool = True
) -> None:
    data = config.model_dump()

    # Ensure enum values are plain strings for YAML serialization
    data["provider"]["kind"] = config.provider.kind.value

    secret_value = config.provider.api_key.get_secret_value()

    if store_key_as_env:
        env_name = _guess_env_name(config.provider.kind)
        data["provider"]["api_key"] = f"${{{env_name}}}"
    else:
        data["provider"]["api_key"] = secret_value

    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    if not store_key_as_env:
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass


def redact(config: AIConfig) -> dict:
    """Return a dict safe for logging — api_key is replaced with '********'."""
    data = config.model_dump()
    data["provider"]["api_key"] = "********"
    return data


def _guess_env_name(kind: ProviderKind) -> str:
    mapping = {
        ProviderKind.OPENAI: "OPENAI_API_KEY",
        ProviderKind.ANTHROPIC: "ANTHROPIC_API_KEY",
        ProviderKind.OPENAI_COMPATIBLE: "COMPAT_API_KEY",
    }
    return mapping.get(kind, "API_KEY")
