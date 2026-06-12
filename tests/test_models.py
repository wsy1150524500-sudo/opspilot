from __future__ import annotations

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from ops_agent.core.models import (
    CpuStats,
    MemoryStats,
    DiskStats,
    SystemSnapshot,
    CommandResult,
    HostConfig,
    AppConfig,
)


# ── Property 1: Percent bounds ──────────────────────────────────────

@given(
    cpu_pct=st.floats(min_value=0, max_value=100),
    mem_pct=st.floats(min_value=0, max_value=100),
    disk_pct=st.floats(min_value=0, max_value=100),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_property1_percent_bounds(cpu_pct, mem_pct, disk_pct):
    cpu = CpuStats(
        percent=cpu_pct, per_core=[cpu_pct], load_avg=(0.0, 0.0, 0.0), core_count=1
    )
    mem = MemoryStats(total_mb=100, used_mb=50, available_mb=50, percent=mem_pct)
    disk = DiskStats(
        mountpoint="/", total_gb=100, used_gb=50, free_gb=50, percent=disk_pct
    )
    assert 0 <= cpu.percent <= 100
    assert 0 <= mem.percent <= 100
    assert 0 <= disk.percent <= 100


def test_percent_out_of_range_rejected():
    with pytest.raises(Exception):
        CpuStats(percent=101, per_core=[], load_avg=(0, 0, 0), core_count=1)
    with pytest.raises(Exception):
        CpuStats(percent=-1, per_core=[], load_avg=(0, 0, 0), core_count=1)


# ── Property 2: Disk consistency ────────────────────────────────────

@given(
    total=st.floats(min_value=0.01, max_value=1e6),
    used_frac=st.floats(min_value=0, max_value=1),
    free_frac=st.floats(min_value=0, max_value=1),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_property2_disk_consistency(total, used_frac, free_frac):
    used = total * used_frac
    free = total * free_frac
    if used + free > total:
        free = total - used
    disk = DiskStats(
        mountpoint="/",
        total_gb=round(total, 2),
        used_gb=round(used, 2),
        free_gb=round(free, 2),
        percent=round(used / total * 100, 2),
    )
    assert disk.total_gb >= 0
    assert disk.used_gb + disk.free_gb <= disk.total_gb + 0.1  # rounding epsilon


# ── Property 5: Success definition ──────────────────────────────────

@given(
    exit_code=st.integers(min_value=-1, max_value=255),
    has_error=st.booleans(),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_property5_success_definition(exit_code, has_error):
    error_msg = "some error" if has_error else None
    expected_success = exit_code == 0 and error_msg is None

    # Use the factory method to bypass the model_validator check-on-construction
    result = CommandResult.make(
        host="h",
        command="c",
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration_ms=0,
        error=error_msg,
    )
    assert result.success == expected_success


def test_command_result_inconsistent_success_rejected():
    with pytest.raises(Exception):
        CommandResult(
            host="h",
            command="c",
            exit_code=1,
            stdout="",
            stderr="",
            duration_ms=0,
            success=True,  # wrong: exit_code != 0
        )


# ── Property 8: Config auth invariant ───────────────────────────────

@given(
    has_password=st.booleans(),
    has_key=st.booleans(),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_property8_config_auth_invariant(has_password, has_key):
    if not has_password and not has_key:
        with pytest.raises(Exception):
            HostConfig(
                name="h",
                hostname="10.0.0.1",
                username="root",
            )
    else:
        hc = HostConfig(
            name="h",
            hostname="10.0.0.1",
            username="root",
            password="secret" if has_password else None,
            key_path="/tmp/key" if has_key else None,
        )
        assert hc.password is not None or hc.key_path is not None


def test_max_concurrency_must_be_at_least_one():
    with pytest.raises(Exception):
        AppConfig(max_concurrency=0)
    with pytest.raises(Exception):
        AppConfig(max_concurrency=-1)
    config = AppConfig(max_concurrency=1)
    assert config.max_concurrency == 1
