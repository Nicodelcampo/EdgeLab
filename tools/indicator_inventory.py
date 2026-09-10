#!/usr/bin/env python3
"""Render and validate the indicator onboarding inventory."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.onboarding.registry import load_registry, validate_registry  # noqa: E402

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--registry", default=str(REPO / "config/indicator_registry_v1.json"))
    args = ap.parse_args(argv)
    registry = load_registry(args.registry)
    result = validate_registry(registry, REPO if args.check else None)
    print("ID                      STAGE                       PARITY                 NEXT")
    print("-" * 108)
    for entry in registry["indicators"]:
        actions = entry.get("next_actions", [])
        print(f"{entry['id']:<23} {entry['stage']:<27} {entry['parity']['status']:<22} {(actions[0] if actions else '-')}")
    print(f"\nresearch={sum(x['role']=='research_indicator' for x in registry['indicators'])} diagnostics={sum(x['role']=='diagnostic' for x in registry['indicators'])} errors={len(result.errors)} warnings={len(result.warnings)}")
    for warning in result.warnings:
        print("WARN ", warning)
    for error in result.errors:
        print("ERROR", error)
    return 1 if result.errors else 0
if __name__ == "__main__":
    raise SystemExit(main())
