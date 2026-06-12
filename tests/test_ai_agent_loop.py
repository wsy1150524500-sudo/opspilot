from __future__ import annotations

import json

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from ops_agent.ai.agent import AgentRunner
from ops_agent.ai.models import (
    ChatMessage,
    Role,
    ToolCall,
    ToolDefinition,
)
from ops_agent.ai.tool_registry import Tool, ToolRegistry
from tests.fake_provider import FakeProvider, make_final_msg, make_tool_call_msg


def _make_registry(tool_name: str = "echo", result: str = "ok") -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        Tool(
            name=tool_name,
            description="test tool",
            parameters={"type": "object", "properties": {}},
            handler=lambda args: {"result": result},
        )
    )
    return reg


# ── Property 2: Agent loop termination / max-iteration bound ────────

@given(n_tool_calls=st.integers(min_value=0, max_value=15))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property2_loop_termination(n_tool_calls):
    max_iter = 5
    responses = [
        make_tool_call_msg("echo", {}, call_id=f"call_{i}")
        for i in range(n_tool_calls)
    ]
    # Always end with a final answer
    responses.append(make_final_msg("done"))

    provider = FakeProvider(responses=responses)
    registry = _make_registry()
    runner = AgentRunner(provider, registry, max_iterations=max_iter)

    result = runner.run("test message")

    assert result.iterations <= max_iter
    if n_tool_calls < max_iter:
        assert result.stopped_reason == "final_answer"
    else:
        assert result.stopped_reason == "max_iterations"


def test_max_iterations_hits_bound():
    """When model always returns tool calls, loop stops at max_iterations."""
    max_iter = 3
    responses = [make_tool_call_msg("echo", {}) for _ in range(100)]
    provider = FakeProvider(responses=responses)
    registry = _make_registry()
    runner = AgentRunner(provider, registry, max_iterations=max_iter)

    result = runner.run("test")
    assert result.iterations == max_iter
    assert result.stopped_reason == "max_iterations"


# ── Property 4: Tool failure isolation ──────────────────────────────

def test_property4_tool_failure_isolation():
    """A failing tool does not crash the loop; the error is fed back."""
    def _bad_handler(args):
        raise RuntimeError("tool exploded")

    reg = ToolRegistry()
    reg.register(
        Tool(
            name="bad_tool",
            description="fails always",
            parameters={"type": "object", "properties": {}},
            handler=_bad_handler,
        )
    )

    # Model calls bad_tool, gets error, then gives final answer
    provider = FakeProvider(
        responses=[
            make_tool_call_msg("bad_tool", {}),
            make_final_msg("I could not complete the task."),
        ]
    )
    runner = AgentRunner(provider, reg, max_iterations=5)
    result = runner.run("do something")

    assert result.stopped_reason == "final_answer"
    assert len(result.tool_invocations) == 1
    assert result.tool_invocations[0].ok is False
    assert "tool exploded" in result.tool_invocations[0].error


# ── Property 7: Transcript correlation invariant ────────────────────

def test_property7_transcript_correlation():
    """Every TOOL message in transcript has a tool_call_id matching a prior assistant ToolCall."""
    provider = FakeProvider(
        responses=[
            make_tool_call_msg("echo", {"x": 1}, call_id="tc_1"),
            make_final_msg("done"),
        ]
    )
    registry = _make_registry()
    runner = AgentRunner(provider, registry, max_iterations=5)
    result = runner.run("test")

    # Collect all ToolCall ids from assistant messages
    assistant_call_ids: set[str] = set()
    for msg in result.transcript:
        if msg.role == Role.ASSISTANT:
            for tc in msg.tool_calls:
                assistant_call_ids.add(tc.id)

    # Every tool message references one of those ids
    for msg in result.transcript:
        if msg.role == Role.TOOL:
            assert msg.tool_call_id in assistant_call_ids


# ── Unit tests ──────────────────────────────────────────────────────

def test_run_empty_message_raises():
    provider = FakeProvider()
    runner = AgentRunner(provider, _make_registry())
    with pytest.raises(ValueError, match="non-empty"):
        runner.run("")


def test_run_no_tool_calling_support():
    provider = FakeProvider(_supports_tools=False)
    runner = AgentRunner(provider, _make_registry())
    result = runner.run("hello")
    assert result.stopped_reason == "error"
    assert "not support" in result.final_text.lower()


def test_provider_error_returns_error_result():
    from ops_agent.ai.errors import ProviderError

    class ErrorProvider(FakeProvider):
        def chat(self, messages, tools):
            raise ProviderError("API down")

    provider = ErrorProvider()
    runner = AgentRunner(provider, _make_registry(), max_iterations=3)
    result = runner.run("test")
    assert result.stopped_reason == "error"
    assert "Provider error" in result.final_text
