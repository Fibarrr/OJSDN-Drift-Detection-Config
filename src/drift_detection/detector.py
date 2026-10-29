"""Order-independent semantic comparison for intent and observed graphs."""

from __future__ import annotations

from typing import Any

import networkx as nx

from .graph import build_intended_graph, build_observed_graph


def compare_graphs(expected: nx.Graph, observed: nx.Graph) -> list[dict[str, Any]]:
    drift: list[dict[str, Any]] = []
    expected_nodes = set(expected.nodes)
    observed_nodes = set(observed.nodes)

    for node in sorted(expected_nodes - observed_nodes):
        drift.append({"kind": "missing_object", "object": node})
    for node in sorted(observed_nodes - expected_nodes):
        drift.append({"kind": "unexpected_object", "object": node})

    for node in sorted(expected_nodes & observed_nodes):
        expected_attrs = expected.nodes[node]
        observed_attrs = observed.nodes[node]
        keys = (set(expected_attrs) | set(observed_attrs)) - {"type", "router", "name"}
        for key in sorted(keys):
            wanted = expected_attrs.get(key)
            actual = observed_attrs.get(key)
            if wanted != actual:
                drift.append(
                    {
                        "kind": "attribute_changed",
                        "object": node,
                        "attribute": key,
                        "expected": wanted,
                        "observed": actual,
                    }
                )

    shared_nodes = expected_nodes & observed_nodes
    expected_edges = {
        frozenset(edge)
        for edge in expected.edges
        if set(edge).issubset(shared_nodes)
    }
    observed_edges = {
        frozenset(edge)
        for edge in observed.edges
        if set(edge).issubset(shared_nodes)
    }
    for edge in sorted(expected_edges - observed_edges, key=lambda pair: sorted(pair)):
        drift.append({"kind": "missing_relationship", "objects": sorted(edge)})
    for edge in sorted(observed_edges - expected_edges, key=lambda pair: sorted(pair)):
        drift.append({"kind": "unexpected_relationship", "objects": sorted(edge)})
    return drift


def detect_drift(
    baseline: dict[str, Any], live_state: dict[str, Any]
) -> list[dict[str, Any]]:
    return compare_graphs(
        build_intended_graph(baseline), build_observed_graph(live_state, baseline)
    )


def report(baseline: dict[str, Any], live_state: dict[str, Any]) -> dict[str, Any]:
    drift = detect_drift(baseline, live_state)
    return {
        "schema_version": 1,
        "baseline": baseline.get("name", "intent/baseline.yml"),
        "collected_at": live_state.get("collected_at"),
        "drift_count": len(drift),
        "drift": drift,
    }


def format_report(result: dict[str, Any]) -> str:
    if not result["drift"]:
        return f"No configuration drift detected ({result['collected_at'] or 'snapshot has no timestamp'})."
    lines = [f"Detected {result['drift_count']} configuration drift item(s):"]
    for item in result["drift"]:
        if item["kind"] == "attribute_changed":
            lines.append(
                f"- {item['object']} {item['attribute']}: "
                f"expected {item['expected']!r}, observed {item['observed']!r}"
            )
        elif item["kind"] in {"missing_object", "unexpected_object"}:
            lines.append(f"- {item['kind']}: {item['object']}")
        else:
            lines.append(f"- {item['kind']}: {item.get('objects', item.get('object'))}")
    return "\n".join(lines)
