"""Command-line interface for live collection and drift reporting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from .collector import collect_live_state
from .detector import format_report, report


def load_baseline(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as source:
        baseline = yaml.safe_load(source)
    if not isinstance(baseline, dict) or not isinstance(baseline.get("routers"), dict):
        raise ValueError("baseline must contain a routers mapping")
    return baseline


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source)


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drift-detection")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="collect live FRR state as JSON")
    collect.add_argument("--baseline", default="intent/baseline.yml")
    collect.add_argument("--output", default="artifacts/live_state.json")
    collect.add_argument("--container-prefix", default="clab-drift-detection")

    detect = subparsers.add_parser("detect", help="compare a snapshot with intent")
    detect.add_argument("--baseline", default="intent/baseline.yml")
    detect.add_argument("--observed", default="artifacts/live_state.json")
    detect.add_argument("--output", help="optional path for the JSON report")
    detect.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        baseline = load_baseline(args.baseline)
        if args.command == "collect":
            routers = list(baseline["routers"])
            state = collect_live_state(routers)
            _write_json(args.output, state)
            print(f"Collected {len(routers)} router(s) to {args.output}")
            return 0

        result = report(baseline, _read_json(args.observed))
        if args.output:
            _write_json(args.output, result)
        if args.format == "json":
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(format_report(result))
        return 1 if result["drift_count"] else 0
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
