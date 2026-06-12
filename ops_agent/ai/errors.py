from __future__ import annotations


class AIError(Exception):
    """Base exception for the AI agent layer."""


class UnknownProviderError(AIError):
    """Raised when a provider key is not registered."""


class ProviderError(AIError):
    """Raised on provider API call failures."""


class ConfigError(AIError):
    """Raised on invalid AI configuration."""
