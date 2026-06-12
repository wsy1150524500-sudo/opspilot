from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ops_agent.web.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@patch("ops_agent.services.system_service.SystemInspector")
def test_get_system(mock_cls, client):
    from ops_agent.core.models import CpuStats, DiskStats, MemoryStats, SystemSnapshot
    from datetime import datetime, timezone

    snap = SystemSnapshot(
        hostname="test-host",
        collected_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        cpu=CpuStats(percent=10.0, per_core=[10.0], load_avg=(0.1, 0.1, 0.1), core_count=1),
        memory=MemoryStats(total_mb=8000, used_mb=4000, available_mb=4000, percent=50.0),
        disks=[DiskStats(mountpoint="/", total_gb=100, used_gb=50, free_gb=50, percent=50.0)],
    )
    instance = MagicMock()
    instance.collect.return_value = snap
    mock_cls.return_value = instance

    resp = client.get("/api/v1/system")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hostname"] == "test-host"
    assert "cpu" in data
    assert "memory" in data
    assert "disks" in data


def test_analyze_logs_not_found(client):
    resp = client.post(
        "/api/v1/logs/analyze",
        json={"path": "/nonexistent/file.log", "patterns": ["ERROR"]},
    )
    assert resp.status_code == 404


def test_analyze_logs_success(tmp_path: Path, client):
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "2024-01-15 10:00:00 INFO started\n"
        "2024-01-15 10:00:01 ERROR something broke\n",
        encoding="utf-8",
    )

    resp = client.post(
        "/api/v1/logs/analyze",
        json={"path": str(log_file), "patterns": ["ERROR"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_lines"] == 2
    assert len(data["matches"]) == 1
    assert data["matches"][0]["pattern"] == "ERROR"


@patch("ops_agent.services.ssh_service.SSHBatchManager")
def test_ssh_run(mock_mgr_cls, client):
    from ops_agent.core.models import CommandResult

    result = CommandResult.make(
        host="web1",
        command="uptime",
        exit_code=0,
        stdout=" 10:00:00 up 10 days\n",
        stderr="",
        duration_ms=100,
    )
    instance = MagicMock()
    instance.execute.return_value = [result]
    mock_mgr_cls.return_value = instance

    resp = client.post(
        "/api/v1/ssh/run",
        json={
            "command": "uptime",
            "hosts": [
                {
                    "name": "web1",
                    "hostname": "10.0.0.1",
                    "username": "root",
                    "key_path": "/tmp/id_rsa",
                }
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["success"] is True
    assert data[0]["host"] == "web1"
