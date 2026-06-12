from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from ops_agent.core.models import CommandResult, HostConfig
from ops_agent.core.ssh_manager import SSHBatchManager


def _host(name: str, ok: bool = True) -> HostConfig:
    return HostConfig(
        name=name,
        hostname=f"{name}.example.com",
        username="root",
        key_path="/tmp/id_rsa" if ok else "/tmp/id_rsa",
    )


# ── Property 3: Batch completeness and order ───────────────────────

@given(n=st.integers(min_value=1, max_value=10))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@patch("ops_agent.core.ssh_manager.SSHConnection")
def test_property3_batch_completeness_and_order(mock_conn_cls, n):
    hosts = [_host(f"h{i}") for i in range(n)]

    conn_instance = MagicMock()
    conn_instance.open.return_value = conn_instance
    conn_instance.run.return_value = ("ok", "", 0)
    mock_conn_cls.return_value = conn_instance

    mgr = SSHBatchManager(timeout_s=5, max_concurrency=4)
    results = mgr.execute(hosts, "uptime")

    assert len(results) == n
    for i, r in enumerate(results):
        assert r.host == f"h{i}"


# ── Property 4: Failure isolation ──────────────────────────────────

@given(
    n_ok=st.integers(min_value=1, max_value=5),
    n_fail=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@patch("ops_agent.core.ssh_manager.SSHConnection")
def test_property4_failure_isolation(mock_conn_cls, n_ok, n_fail):
    hosts = [_host(f"ok{i}", ok=True) for i in range(n_ok)] + [
        _host(f"bad{i}", ok=False) for i in range(n_fail)
    ]
    total = n_ok + n_fail

    call_count = 0

    def make_conn(host, timeout_s=15):
        nonlocal call_count
        call_count += 1
        conn = MagicMock()
        conn.open.return_value = conn
        if host.name.startswith("bad"):
            conn.open.side_effect = ConnectionError(f"Cannot reach {host.name}")
        else:
            conn.run.return_value = ("ok", "", 0)
        return conn

    mock_conn_cls.side_effect = make_conn

    mgr = SSHBatchManager(timeout_s=5, max_concurrency=4)
    results = mgr.execute(hosts, "uptime")

    assert len(results) == total
    for r in results:
        if r.host.startswith("bad"):
            assert r.success is False
            assert r.error is not None


# ── Unit tests ──────────────────────────────────────────────────────

@patch("ops_agent.core.ssh_manager.SSHConnection")
def test_execute_single_success(mock_conn_cls):
    conn = MagicMock()
    conn.open.return_value = conn
    conn.run.return_value = ("hello\n", "", 0)
    mock_conn_cls.return_value = conn

    mgr = SSHBatchManager(timeout_s=5, max_concurrency=1)
    results = mgr.execute([_host("web1")], "echo hello")

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].exit_code == 0
    assert results[0].stdout == "hello\n"


@patch("ops_agent.core.ssh_manager.SSHConnection")
def test_execute_auth_failure(mock_conn_cls):
    conn = MagicMock()
    conn.open.side_effect = Exception("Authentication failed")
    mock_conn_cls.return_value = conn

    mgr = SSHBatchManager(timeout_s=5, max_concurrency=1)
    results = mgr.execute([_host("badhost")], "whoami")

    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error is not None
    assert "Authentication failed" in results[0].error
    assert results[0].exit_code == -1


def test_execute_empty_command_raises():
    mgr = SSHBatchManager()
    with pytest.raises(ValueError, match="non-empty"):
        mgr.execute([_host("h1")], "")


def test_execute_invalid_concurrency_raises():
    with pytest.raises(ValueError, match="max_concurrency"):
        SSHBatchManager(max_concurrency=0)
