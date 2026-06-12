from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import paramiko

from ops_agent.core.models import CommandResult, HostConfig


class SSHConnection:
    def __init__(self, host: HostConfig, timeout_s: int = 15) -> None:
        self._host = host
        self._timeout_s = timeout_s
        self._client: paramiko.SSHClient | None = None

    def open(self) -> SSHConnection:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict = {
            "hostname": self._host.hostname,
            "port": self._host.port,
            "username": self._host.username,
            "timeout": self._timeout_s,
        }
        if self._host.password:
            connect_kwargs["password"] = self._host.password
        if self._host.key_path:
            connect_kwargs["key_filename"] = self._host.key_path
        client.connect(**connect_kwargs)
        self._client = client
        return self

    def run(self, command: str) -> tuple[str, str, int]:
        assert self._client is not None
        _, stdout_ch, stderr_ch = self._client.exec_command(
            command, timeout=self._timeout_s
        )
        exit_code = stdout_ch.channel.recv_exit_status()
        stdout = stdout_ch.read().decode("utf-8", errors="replace")
        stderr = stderr_ch.read().decode("utf-8", errors="replace")
        return stdout, stderr, exit_code

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


class SSHBatchManager:
    def __init__(self, timeout_s: int = 15, max_concurrency: int = 10) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._timeout_s = timeout_s
        self._max_concurrency = max_concurrency

    def execute(
        self, hosts: list[HostConfig], command: str
    ) -> list[CommandResult]:
        if not command:
            raise ValueError("command must be non-empty")
        if self._max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")

        workers = min(self._max_concurrency, len(hosts))
        results: list[CommandResult] = [None] * len(hosts)  # type: ignore[list-item]

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {
                pool.submit(self.execute_one, host, command): idx
                for idx, host in enumerate(hosts)
            }
            for future in future_map:
                idx = future_map[future]
                results[idx] = future.result()

        return results

    def execute_one(
        self, host: HostConfig, command: str
    ) -> CommandResult:
        start = time.monotonic_ns()
        try:
            conn = SSHConnection(host, timeout_s=self._timeout_s).open()
            stdout, stderr, exit_code = conn.run(command)
            conn.close()
            elapsed_ms = (time.monotonic_ns() - start) // 1_000_000
            return CommandResult.make(
                host=host.name,
                command=command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic_ns() - start) // 1_000_000
            return CommandResult.make(
                host=host.name,
                command=command,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=elapsed_ms,
                error=str(exc),
            )
