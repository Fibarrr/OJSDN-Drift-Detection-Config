"""Build comparable NetworkX graphs from intended and collected config state."""

from __future__ import annotations

import ipaddress
from typing import Any

import networkx as nx


def _addresses(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(str(ipaddress.ip_interface(value)) for value in values))


def _prefix(value: str) -> str:
    return str(ipaddress.ip_network(value, strict=False))


def build_intended_graph(baseline: dict[str, Any]) -> nx.Graph:
    graph = nx.Graph()
    common_ospf = baseline.get("ospf", {})
    default_area = str(common_ospf.get("area", "0.0.0.0"))
    default_passive = tuple(sorted(common_ospf.get("passive_interfaces", [])))

    for router, config in sorted(baseline["routers"].items()):
        router_node = f"router/{router}"
        networks = tuple(
            sorted(
                ( _prefix(network), default_area)
                for network in config.get("ospf", {}).get("networks", [])
            )
        )
        graph.add_node(
            router_node,
            type="router",
            router_id=str(ipaddress.ip_address(config["router_id"])),
            ospf={
                "router_id": str(
                    ipaddress.ip_address(config.get("ospf", {}).get("router_id", config["router_id"]))
                ),
                "networks": networks,
                "passive_interfaces": tuple(
                    sorted(config.get("ospf", {}).get("passive_interfaces", default_passive))
                ),
            },
        )
        for interface, attrs in sorted(config.get("interfaces", {}).items()):
            interface_node = f"interface/{router}/{interface}"
            graph.add_node(
                interface_node,
                type="interface",
                router=router,
                name=interface,
                addresses=_addresses(attrs.get("addresses", [])),
                admin_up=bool(attrs.get("admin_up", attrs.get("status", "up") == "up")),
                mtu=int(attrs["mtu"]) if attrs.get("mtu") is not None else None,
            )
            graph.add_edge(router_node, interface_node, relation="owns")

        for route in config.get("static_routes", []):
            prefix = _prefix(route["prefix"])
            next_hop = str(ipaddress.ip_address(route["next_hop"]))
            distance = int(route.get("distance", 1))
            route_node = f"static-route/{router}/{prefix}/{next_hop}/{distance}"
            graph.add_node(
                route_node,
                type="static_route",
                router=router,
                prefix=prefix,
                next_hop=next_hop,
                distance=distance,
            )
            graph.add_edge(router_node, route_node, relation="configures")
    return graph


def build_observed_graph(
    live_state: dict[str, Any], baseline: dict[str, Any]
) -> nx.Graph:
    graph = nx.Graph()
    management_interface = baseline.get("management_interface")
    default_area = str(baseline.get("ospf", {}).get("area", "0.0.0.0"))
    default_passive = tuple(sorted(baseline.get("ospf", {}).get("passive_interfaces", [])))

    for router, record in sorted(live_state["routers"].items()):
        config = record["configuration"]
        ospf = config.get("ospf", {})
        router_id = ospf.get("router_id")
        networks = tuple(
            sorted(
                (
                    _prefix(entry["prefix"]),
                    str(entry.get("area", default_area)),
                )
                for entry in ospf.get("networks", [])
            )
        )
        router_node = f"router/{router}"
        graph.add_node(
            router_node,
            type="router",
            router_id=router_id,
            ospf={
                "router_id": router_id,
                "networks": networks,
                "passive_interfaces": tuple(
                    sorted(ospf.get("passive_interfaces", default_passive))
                ),
            },
        )

        for interface, attrs in sorted(config.get("interfaces", {}).items()):
            if interface == management_interface:
                continue
            interface_node = f"interface/{router}/{interface}"
            graph.add_node(
                interface_node,
                type="interface",
                router=router,
                name=interface,
                addresses=_addresses(attrs.get("addresses", [])),
                admin_up=bool(attrs.get("admin_up", False)),
                mtu=int(attrs["mtu"]) if attrs.get("mtu") is not None else None,
            )
            graph.add_edge(router_node, interface_node, relation="owns")

        for route in config.get("static_routes", []):
            prefix = _prefix(route["prefix"])
            next_hop = str(ipaddress.ip_address(route["next_hop"]))
            distance = int(route.get("distance", 1))
            route_node = f"static-route/{router}/{prefix}/{next_hop}/{distance}"
            graph.add_node(
                route_node,
                type="static_route",
                router=router,
                prefix=prefix,
                next_hop=next_hop,
                distance=distance,
            )
            graph.add_edge(router_node, route_node, relation="configures")
    return graph
