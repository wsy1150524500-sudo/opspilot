from __future__ import annotations

import os
import re

import yaml

from ops_agent.core.models import AppConfig, HostConfig

_ENV_PATTERN = re.compile(r"\$\{(\w+)\}")


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):
        def _replace(m: re.Match) -> str:
            env_val = os.environ.get(m.group(1), "")
            return env_val
        return _ENV_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _substitute_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env(item) for item in value]
    return value


def load_config(path: str | None = None) -> AppConfig:
    if path is None:
        return AppConfig()

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        return AppConfig()

    raw = _substitute_env(raw)
    return AppConfig.model_validate(raw)


def find_host(config: AppConfig, name: str) -> HostConfig:
    for h in config.hosts:
        if h.name == name:
            return h
    raise KeyError(f"Host '{name}' not found in config")
