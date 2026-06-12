from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ops_agent.core.system_inspector import SystemInspector


def _make_mock_psutil():
    """Build a mock psutil module returning realistic structures."""
    psutil = MagicMock()

    psutil.cpu_percent.side_effect = [42.5, [40.0, 45.0]]
    psutil.getloadavg.return_value = (1.0, 0.8, 0.5)
    psutil.cpu_count.return_value = 2

    vm = MagicMock()
    vm.total = 8 * 1024 * 1024 * 1024  # 8 GB
    vm.used = 4 * 1024 * 1024 * 1024
    vm.available = 4 * 1024 * 1024 * 1024
    vm.percent = 50.0
    psutil.virtual_memory.return_value = vm

    part = MagicMock()
    part.mountpoint = "/"
    psutil.disk_partitions.return_value = [part]

    usage = MagicMock()
    usage.total = 100 * 1024**3
    usage.used = 60 * 1024**3
    usage.free = 40 * 1024**3
    usage.percent = 60.0
    psutil.disk_usage.return_value = usage

    return psutil


@patch("ops_agent.core.system_inspector.psutil")
def test_collect_returns_valid_snapshot(mock_psutil):
    mock_psutil_obj = _make_mock_psutil()
    mock_psutil.cpu_percent = mock_psutil_obj.cpu_percent
    mock_psutil.getloadavg = mock_psutil_obj.getloadavg
    mock_psutil.cpu_count = mock_psutil_obj.cpu_count
    mock_psutil.virtual_memory = mock_psutil_obj.virtual_memory
    mock_psutil.disk_partitions = mock_psutil_obj.disk_partitions
    mock_psutil.disk_usage = mock_psutil_obj.disk_usage

    inspector = SystemInspector(cpu_sample_interval=0)
    snapshot = inspector.collect()

    assert snapshot.hostname
    assert snapshot.collected_at is not None
    assert 0 <= snapshot.cpu.percent <= 100
    assert 0 <= snapshot.memory.percent <= 100
    assert len(snapshot.disks) >= 1
    for d in snapshot.disks:
        assert 0 <= d.percent <= 100


@patch("ops_agent.core.system_inspector.psutil")
def test_collect_cpu(mock_psutil):
    obj = _make_mock_psutil()
    mock_psutil.cpu_percent = obj.cpu_percent
    mock_psutil.getloadavg = obj.getloadavg
    mock_psutil.cpu_count = obj.cpu_count

    inspector = SystemInspector(cpu_sample_interval=0)
    cpu = inspector.collect_cpu()

    assert cpu.percent == 42.5
    assert cpu.per_core == [40.0, 45.0]
    assert cpu.core_count == 2
    assert cpu.load_avg == (1.0, 0.8, 0.5)


@patch("ops_agent.core.system_inspector.psutil")
def test_collect_memory(mock_psutil):
    obj = _make_mock_psutil()
    mock_psutil.virtual_memory = obj.virtual_memory

    inspector = SystemInspector()
    mem = inspector.collect_memory()

    assert mem.total_mb > 0
    assert mem.used_mb > 0
    assert 0 <= mem.percent <= 100


@patch("ops_agent.core.system_inspector.psutil")
def test_collect_disks_skips_inaccessible(mock_psutil):
    part_ok = MagicMock()
    part_ok.mountpoint = "/ok"
    part_bad = MagicMock()
    part_bad.mountpoint = "/bad"
    mock_psutil.disk_partitions.return_value = [part_ok, part_bad]

    usage = MagicMock()
    usage.total = 100 * 1024**3
    usage.used = 50 * 1024**3
    usage.free = 50 * 1024**3
    usage.percent = 50.0

    def disk_usage_side_effect(mp):
        if mp == "/bad":
            raise PermissionError("denied")
        return usage

    mock_psutil.disk_usage.side_effect = disk_usage_side_effect

    inspector = SystemInspector()
    disks = inspector.collect_disks()

    assert len(disks) == 1
    assert disks[0].mountpoint == "/ok"


@patch("ops_agent.core.system_inspector.psutil")
def test_collect_disks_with_explicit_mountpoints(mock_psutil):
    usage = MagicMock()
    usage.total = 200 * 1024**3
    usage.used = 100 * 1024**3
    usage.free = 100 * 1024**3
    usage.percent = 50.0
    mock_psutil.disk_usage.return_value = usage

    inspector = SystemInspector()
    disks = inspector.collect_disks(mountpoints=["/mnt/data"])

    assert len(disks) == 1
    assert disks[0].mountpoint == "/mnt/data"
