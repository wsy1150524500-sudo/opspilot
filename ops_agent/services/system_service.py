from __future__ import annotations

from ops_agent.core.system_inspector import SystemInspector
from ops_agent.core.models import SystemSnapshot


class SystemService:
    def snapshot(self) -> SystemSnapshot:
        return SystemInspector().collect()
