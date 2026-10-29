"""Small, explicit normalizers for FRR JSON and selected running-config lines."""

from __future__ import annotations

import ipaddress
import json
import re
from typing import Any


def extract_json(output: str) -> Any:
    """Decode the first JSON value in FRR output, ignoring vtysh warnings."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character in "[{":
            try:
                value, _ = decoder.raw_decode(output[index:])
                return value
            except json.JSONDecodeError:
                continue
    raise ValueError("FRR output did not contain a JSON value")


def normalize_interfaces(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize `show interface json` to stable IPv4/admin/MTU attributes."""
    result: dict[str, dict[str, Any]] = {}
    for name, raw in payload.items():
        addresses = sorted(
            str(item["address"])
            for item in raw.get("ipAddresses", [])
            if ":" not in str(item.get("address", ""))
        )
        admin = raw.get("administrativeStatus")
        if admin is None:
            admin = "up" if "UP" in str(raw.get("flags", "")).split(",") else "down"
        oper = raw.get("operationalStatus")
        if oper is None:
            oper = "up" if "LOWER_UP" in str(raw.get("flags", "")) else "down"
        result[name] = {
            "addresses": addresses,
            "admin_up": str(admin).lower() == "up",
            "oper_up": str(oper).lower() == "up",
            "mtu": int(raw.get("mtu", 0)),
        }
    return dict(sorted(result.items()))


def _normalize_prefix(value: str) -> str:
    return str(ipaddress.ip_network(value, strict=False))


def normalize_operational_routes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize FRR route JSON without conflating learned routes with intent."""
    routes: list[dict[str, Any]] = []
    for prefix, entries in payload.items():
        for entry in entries if isinstance(entries, list) else []:
            next_hops = []
            for hop in entry.get("nexthops", []):
                address = hop.get("ip")
                next_hops.append(
                    {
                        "ip": str(ipaddress.ip_address(address)) if address else None,
                        "interface": hop.get("interfaceName"),
                    }
                )
            routes.append(
                {
                    "prefix": _normalize_prefix(entry.get("prefix", prefix)),
                    "protocol": str(entry.get("protocol", "unknown")),
                    "selected": bool(entry.get("selected", False)),
                    "installed": bool(entry.get("installed", False)),
                    "next_hops": sorted(
                        next_hops,
                        key=lambda item: (item["ip"] or "", item["interface"] or ""),
                    ),
                }
            )
    return sorted(routes, key=lambda item: (item["prefix"], item["protocol"], item["next_hops"][0]["ip"] if item["next_hops"] else ""))


_STATIC_ROUTE = re.compile(r"^ip route (?:vrf \S+ )?(\S+) (\S+)(?: (\d+))?(?: tag \d+)?$")
_OSPF_NETWORK = re.compile(r"^network (\S+(?: \S+)?) area (\S+)$")


def _normalize_ospf_network(value: str) -> str:
    """Accept CIDR or FRR address/wildcard syntax and return canonical CIDR."""
    if "/" in value:
        return _normalize_prefix(value)
    address, wildcard = value.split()
    wildcard_address = ipaddress.IPv4Address(wildcard)
    netmask = ipaddress.IPv4Address(int(wildcard_address) ^ 0xFFFFFFFF)
    return str(ipaddress.IPv4Network(f"{address}/{netmask}", strict=False))


def parse_running_config(text: str) -> dict[str, Any]:
    """Extract static routes and OSPF intent from FRR's running-config text."""
    routes: set[tuple[str, str, int]] = set()
    networks: set[tuple[str, str]] = set()
    passive: set[str] = set()
    router_id: str | None = None
    in_ospf = False
    current_interface: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("router "):
            in_ospf = line == "router ospf"
            current_interface = None
            continue
        if line.startswith("interface "):
            in_ospf = False
            current_interface = line.split(maxsplit=1)[1]
            continue
        if line.startswith("ip route "):
            match = _STATIC_ROUTE.match(line)
            if match:
                prefix, next_hop, distance = match.groups()
                routes.add(
                    (
                        _normalize_prefix(prefix),
                        str(ipaddress.ip_address(next_hop)),
                        int(distance or 1),
                    )
                )
            continue
        if not in_ospf:
            if current_interface and line == "ip ospf passive":
                passive.add(current_interface)
            continue
        if line.startswith("ospf router-id "):
            router_id = str(ipaddress.ip_address(line.split()[-1]))
        elif line.startswith("passive-interface "):
            passive.add(line.split()[-1])
        else:
            match = _OSPF_NETWORK.match(line)
            if match:
                network_text, area = match.groups()
                network = _normalize_ospf_network(network_text)
                networks.add((network, area))

    return {
        "static_routes": [
            {"prefix": prefix, "next_hop": next_hop, "distance": distance}
            for prefix, next_hop, distance in sorted(routes)
        ],
        "ospf": {
            "router_id": router_id,
            "networks": [
                {"prefix": prefix, "area": area} for prefix, area in sorted(networks)
            ],
            "passive_interfaces": sorted(passive),
        },
    }
