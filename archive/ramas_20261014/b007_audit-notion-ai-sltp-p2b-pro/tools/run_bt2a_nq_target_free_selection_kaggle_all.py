#!/usr/bin/env python3
"""Kaggle sequential orchestrator for the BT2A NQ target-free selection campaign.

The generic frozen-execution envelope (edgelab/kaggle/execution.py) invokes exactly
one argv per campaign. The underlying selection runner
(tools/run_bt2a_nq_target_free_selection.py) is checkpointed per contract and
requires one invocation per contract plus a separate --finalize pass. This
orchestrator sequences those calls, unmodified, inside one Kaggle job so the
campaign fits the single-argv execution contract without touching the
selection runner's own logic.

Each sub-invocation is the exact same script a human would run by hand; this
file adds no research logic of its own. EDGELAB_AUTHORIZATION_TOKEN is
inherited from the parent process environment (set by run_kaggle_frozen_job.py)
and passed through unchanged to every sub-invocation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CONTRACTS = ["NQ 09-25", "NQ 12-25", "NQ 03-26", "NQ 06-26", "NQ 09-26"]
RUNNER = Path(__file__).resolve().parent / "run_bt2a_nq_target_free_selection.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args(argv)

    base = [
        sys.executable,
        str(RUNNER),
        "--data-dir", args.data_dir,
        "--output-dir", args.output_dir,
        "--expected-commit", args.expected_commit,
    ]

    for contract in CONTRACTS:
        print(f"=== contract: {contract} ===", flush=True)
        subprocess.run(base + ["--contract", contract, "--resume"], check=True)

    print("=== finalize ===", flush=True)
    subprocess.run(base + ["--finalize"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
