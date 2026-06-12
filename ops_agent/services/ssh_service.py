from __future__ import annotations

from ops_agent.core.config import find_host
from ops_agent.core.models import AppConfig, CommandResult, HostConfig
from ops_agent.core.ssh_manager import SSHBatchManager
from ops_agent.web.schemas import BatchRunRequest


class SSHService:
    def run_batch(
        self, req: BatchRunRequest, config: AppConfig
    ) -> list[CommandResult]:
        hosts = self._resolve_hosts(req, config)
        mgr = SSHBatchManager(
            timeout_s=config.ssh_timeout_s,
            max_concurrency=config.max_concurrency,
        )
        return mgr.execute(hosts, req.command)

    @staticmethod
    def _resolve_hosts(
        req: BatchRunRequest, config: AppConfig
    ) -> list[HostConfig]:
        hosts: list[HostConfig] = list(req.hosts)
        for name in req.host_names:
            hosts.append(find_host(config, name))
        if not hosts:
            raise ValueError(
                "No hosts specified: provide hosts inline or host_names from config"
            )
        return hosts
