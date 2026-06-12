from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ops_agent.ai.agent import AgentRunner
from ops_agent.ai.models import (
    AIConfig,
    ChatMessage,
    ProviderConfig,
    ProviderKind,
    Role,
)
from ops_agent.ai.tools import build_default_registry
from ops_agent.core.models import AppConfig
from ops_agent.web.server import create_app
from tests.fake_provider import FakeProvider, make_final_msg


def _make_runner(responses=None) -> AgentRunner:
    if responses is None:
        responses = [make_final_msg("System looks healthy.")]
    provider = FakeProvider(responses=responses)
    app_config = AppConfig()
    ai_config = AIConfig(
        provider=ProviderConfig(
            kind=ProviderKind.OPENAI,
            api_key=SecretStr("fake"),
            model="fake",
        )
    )
    registry = build_default_registry(ai_config, app_config)
    return AgentRunner(provider, registry, max_iterations=5)


@pytest.fixture
def client():
    app = create_app()
    runner = _make_runner()
    app.dependency_overrides[lambda: None] = lambda: runner

    # Override the dependency in the ai router
    from ops_agent.web.routers.ai import _get_runner_dependency
    app.dependency_overrides[_get_runner_dependency] = lambda: runner

    return TestClient(app)


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ai_chat_endpoint(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "check system health"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_text"] == "System looks healthy."
    assert data["stopped_reason"] == "final_answer"
    assert "transcript" in data
    assert "tool_invocations" in data


def test_ai_chat_with_tool_calls():
    from ops_agent.ai.models import ToolCall
    from ops_agent.web.routers.ai import _get_runner_dependency

    app = create_app()
    runner = _make_runner(
        responses=[
            ChatMessage(
                role=Role.ASSISTANT,
                content=None,
                tool_calls=[ToolCall(id="c1", name="inspect_system", arguments={})],
            ),
            make_final_msg("CPU is at 10%, memory at 50%."),
        ]
    )
    app.dependency_overrides[_get_runner_dependency] = lambda: runner
    client = TestClient(app)

    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "how is the system?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stopped_reason"] == "final_answer"
    assert len(data["tool_invocations"]) == 1


def test_ai_chat_no_config_returns_503():
    from ops_agent.web.routers.ai import _get_runner_dependency

    app = create_app()

    def _no_config():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="AI agent not configured")

    app.dependency_overrides[_get_runner_dependency] = _no_config
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "test"},
    )
    assert resp.status_code == 503
