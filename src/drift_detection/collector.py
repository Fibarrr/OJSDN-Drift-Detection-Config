"""Read live configuration and operational state from FRR containers."""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any, Protocol

from .parsers import (
    extract_json,
    normalize_interfaces,
    normalize_operational_routes,
    parse_running_config,
)


class CommandRunner(Protocol):
    def run(self, router: str, command: list[str]) -> str: ...


class DockerExecRunner:
    """Run vtysh in a named FRR container (Docker in WSL on Windows)."""

    def __init__(self, container_prefix: str = "clab-drift-detection") -> None:
        self.container_prefix = container_prefix

    def _base_command(self) -> list[str]:
        if platform.system() == "Windows":
            distro = os.environ.get("DRIFT_WSL_DISTRO")
            base = ["wsl.exe"]
            if distro:
                base.extend(["-d", distro])
            return base + ["-e", "docker"]
        return [os.environ.get("DRIFT_DOCKER_BIN", "docker")]

    def run(self, router: str, command: list[str]) -> str:
        container = f"{self.container_prefix}-{router}"
        completed = subprocess.run(
            self._base_command() + ["exec", container, *command],
            check=True,
            capture_output=True,
            text=True,
            timeout=45,
        )
        return completed.stdout


def collect_router(router: str, runner: CommandRunner) -> dict[str, Any]:
    interface_payload = extract_json(
        runner.run(router, ["vtysh", "-c", "show interface json"])
    )
    route_payload = extract_json(
        runner.run(router, ["vtysh", "-c", "show ip route json"])
    )
    running_config = runner.run(router, ["vtysh", "-c", "show running-config"])
    parsed_config = parse_running_config(running_config)
    interfaces = normalize_interfaces(interface_payload)

    return {
        "configuration": {
            "interfaces": {
                name: {
                    "addresses": data["addresses"],
                    "admin_up": data["admin_up"],
                    "mtu": data["mtu"],
                }
                for name, data in interfaces.items()
            },
            "static_routes": parsed_config["static_routes"],
            "ospf": parsed_config["ospf"],
        },
        "operational": {
            "interface_status": {
                name: {"oper_up": data["oper_up"]}
                for name, data in interfaces.items()
            },
            "routing_table": normalize_operational_routes(route_payload),
        },
    }


def collect_live_state(
    routers: list[str],
    runner: CommandRunner | None = None,
    collected_at: str | None = None,
) -> dict[str, Any]:
    """Collect a deterministic router map plus a separately timestamped sample."""
    runner = runner or DockerExecRunner()
    return {
        "schema_version": 1,
        "collected_at": collected_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "routers": {
            router: collect_router(router, runner) for router in sorted(routers)
        },
    }
