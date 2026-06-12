from __future__ import annotations

import logging
import platform
from datetime import datetime, timezone

import psutil

from ops_agent.core.models import CpuStats, DiskStats, MemoryStats, SystemSnapshot

logger = logging.getLogger(__name__)


class SystemInspector:
    def __init__(self, cpu_sample_interval: float = 0.5) -> None:
        self._cpu_sample_interval = cpu_sample_interval

    def collect(self) -> SystemSnapshot:
        return SystemSnapshot(
            hostname=platform.node(),
            collected_at=datetime.now(timezone.utc),
            cpu=self.collect_cpu(),
            memory=self.collect_memory(),
            disks=self.collect_disks(),
        )

    def collect_cpu(self) -> CpuStats:
        percent = psutil.cpu_percent(interval=self._cpu_sample_interval)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        load_avg = psutil.getloadavg()
        return CpuStats(
            percent=percent,
            per_core=per_core,
            load_avg=load_avg,
            core_count=psutil.cpu_count(),
        )

    def collect_memory(self) -> MemoryStats:
        vm = psutil.virtual_memory()
        return MemoryStats(
            total_mb=vm.total / (1024 * 1024),
            used_mb=vm.used / (1024 * 1024),
            available_mb=vm.available / (1024 * 1024),
            percent=vm.percent,
        )

    def collect_disks(
        self, mountpoints: list[str] | None = None
    ) -> list[DiskStats]:
        results: list[DiskStats] = []

        if mountpoints is None:
            partitions = psutil.disk_partitions()
            targets = [p.mountpoint for p in partitions]
        else:
            targets = mountpoints

        for mp in targets:
            try:
                usage = psutil.disk_usage(mp)
                results.append(
                    DiskStats(
                        mountpoint=mp,
                        total_gb=usage.total / (1024**3),
                        used_gb=usage.used / (1024**3),
                        free_gb=usage.free / (1024**3),
                        percent=usage.percent,
                    )
                )
            except (PermissionError, OSError):
                logger.warning("Skipping inaccessible mountpoint: %s", mp)

        return results
