from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from tests.fake_provider import ensure_fake_provider


@pytest.fixture(autouse=True)
def _ensure_providers():
    """Ensure all providers are registered for every test."""
    ensure_fake_provider()


@pytest.fixture
def sample_log_path(tmp_path: Path) -> str:
    lines = [
        "2024-01-15 10:00:00 INFO Application started",
        "2024-01-15 10:00:01 WARNING Disk usage high",
        "2024-01-15 10:00:02 ERROR Connection failed to db",
        "2024-01-15 10:00:03 INFO Request processed",
        "2024-01-15 10:00:04 ERROR Timeout waiting for response",
        "no-timestamp-line DEBUG some debug info",
        "2024-01-15 10:00:05 CRITICAL System overload",
    ]
    p = tmp_path / "test.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


@pytest.fixture
def host_config_factory():
    def _make(name: str = "test", hostname: str = "127.0.0.1", **kwargs):
        from ops_agent.core.models import HostConfig

        defaults = dict(
            name=name,
            hostname=hostname,
            username="root",
            key_path="/tmp/id_rsa",
        )
        defaults.update(kwargs)
        return HostConfig(**defaults)

    return _make
