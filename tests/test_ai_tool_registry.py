from __future__ import annotations

import json

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from ops_agent.ai.models import ToolCall, ToolResult
from ops_agent.ai.tool_registry import Tool, ToolRegistry


# ── Property 3: Tool dispatch maps name → correct service ───────────

@given(
    n_tools=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property3_dispatch_name_mapping(n_tools):
    reg = ToolRegistry()
    for i in range(n_tools):
        name = f"tool_{i}"
        reg.register(
            Tool(
                name=name,
                description=f"tool {i}",
                parameters={"type": "object", "properties": {}},
                handler=lambda args, n=name: {"tool_name": n},
            )
        )

    for i in range(n_tools):
        name = f"tool_{i}"
        call = ToolCall(id=f"call_{i}", name=name, arguments={})
        result = reg.dispatch(call)
        assert result.name == name
        assert result.tool_call_id == f"call_{i}"
        assert result.ok is True
        payload = json.loads(result.content)
        assert payload["tool_name"] == name


# ── Property 4: Tool failure isolation ──────────────────────────────

@given(
    error_msg=st.text(min_size=1, max_size=100),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property4_handler_raises_returns_error(error_msg):
    def _fail(args):
        raise RuntimeError(error_msg)

    reg = ToolRegistry()
    reg.register(
        Tool(
            name="fail",
            description="fails",
            parameters={"type": "object", "properties": {}},
            handler=_fail,
        )
    )

    call = ToolCall(id="c1", name="fail", arguments={})
    result = reg.dispatch(call)
    assert result.ok is False
    assert result.error is not None
    assert error_msg in result.error


def test_dispatch_unknown_tool():
    reg = ToolRegistry()
    call = ToolCall(id="c1", name="nonexistent", arguments={})
    result = reg.dispatch(call)
    assert result.ok is False
    assert "unknown tool" in result.error


# ── Property 5: Health check is definite ────────────────────────────

def test_property5_health_check_returns_definite():
    from tests.fake_provider import FakeProvider

    provider = FakeProvider()
    result = provider.health_check()
    assert result.ok in (True, False)
    assert result.latency_ms >= 0


# ── Unit tests ──────────────────────────────────────────────────────

def test_schemas_returns_unique_names():
    reg = ToolRegistry()
    for name in ["a", "b", "c"]:
        reg.register(
            Tool(
                name=name,
                description=f"tool {name}",
                parameters={"type": "object", "properties": {}},
                handler=lambda args: {},
            )
        )
    schemas = reg.schemas()
    names = [s.name for s in schemas]
    assert len(names) == len(set(names)) == 3


def test_dispatch_result_correlation():
    reg = ToolRegistry()
    reg.register(
        Tool(
            name="echo",
            description="echo",
            parameters={"type": "object", "properties": {}},
            handler=lambda args: args,
        )
    )
    call = ToolCall(id="unique_id_123", name="echo", arguments={"x": 42})
    result = reg.dispatch(call)
    assert result.tool_call_id == "unique_id_123"
    assert result.name == "echo"
