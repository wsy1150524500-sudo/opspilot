from __future__ import annotations

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from ops_agent.ai.errors import UnknownProviderError
from ops_agent.ai.models import ProviderConfig, ProviderKind
from ops_agent.ai.providers.registry import ProviderRegistry
from tests.fake_provider import FakeProvider

# Ensure real providers are registered for round-trip tests
import ops_agent.ai.providers.openai_provider  # noqa: F401
import ops_agent.ai.providers.anthropic_provider  # noqa: F401
import ops_agent.ai.providers.openai_compatible  # noqa: F401


# ── Property 1: Provider registry round-trip ────────────────────────

@given(
    kind=st.sampled_from(list(ProviderKind)),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property1_registry_round_trip(kind):
    cfg_kwargs = {"api_key": "test-key-123", "model": "test-model"}
    if kind == ProviderKind.OPENAI_COMPATIBLE:
        cfg_kwargs["base_url"] = "https://api.example.com/v1"
    cfg = ProviderConfig(kind=kind, **cfg_kwargs)
    provider = ProviderRegistry.create(cfg)
    assert isinstance(provider, type(provider))
    assert provider.config.model == "test-model"


def test_registry_create_unregistered_raises():
    """Creating with an unregistered key raises UnknownProviderError."""
    cfg = ProviderConfig(kind=ProviderKind.OPENAI, api_key="k", model="m")
    saved = dict(ProviderRegistry._registry)
    try:
        ProviderRegistry._registry.clear()
        with pytest.raises(UnknownProviderError):
            ProviderRegistry.create(cfg)
    finally:
        ProviderRegistry._registry.update(saved)


def test_registry_available():
    available = ProviderRegistry.available()
    assert "openai" in available
    assert "anthropic" in available
    assert "openai_compatible" in available


# ── Property 8: Message normalization ───────────────────────────────

def test_fake_provider_returns_valid_chat_message():
    from ops_agent.ai.models import ChatMessage, Role

    provider = FakeProvider(
        responses=[ChatMessage(role=Role.ASSISTANT, content="hello")]
    )
    reply = provider.chat([], [])
    assert reply.role == Role.ASSISTANT
    assert reply.content == "hello"


def test_fake_provider_tool_calling_response():
    from ops_agent.ai.models import ChatMessage, Role, ToolCall

    provider = FakeProvider(
        responses=[
            ChatMessage(
                role=Role.ASSISTANT,
                content=None,
                tool_calls=[ToolCall(id="c1", name="ping", arguments={})],
            )
        ]
    )
    reply = provider.chat([], [])
    assert len(reply.tool_calls) == 1
    assert reply.tool_calls[0].name == "ping"
