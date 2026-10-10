#!/usr/bin/env python3
"""CPU exploratory outcome runner with a supplied frozen split.

This is not an input-file/features firewall or authority to open market data.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.funnel.runner import FunnelRunner
from edgelab.funnel.splits import load_frozen_split, validate_split


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arrays", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--split", required=True, help="Original frozen split JSON; does not grant data permission")
    parser.add_argument("--out", required=True)
    parser.add_argument("--backend", choices=["cpu"], default="cpu")
    parser.add_argument("--max-hold-bars", type=int, default=200)
    parser.add_argument("--max-matrix-bytes", type=int, default=512*1024*1024)
    args = parser.parse_args()
    root = Path(args.arrays)
    load = lambda name: np.load(root / f"{name}.npy", mmap_mode="r", allow_pickle=False)
    frozen = load_frozen_split(args.split)
    trade_dates = load("trade_date")
    validate_split(frozen, trade_dates)  # Reject changed labels before opening price arrays.
    registry = json.loads(Path(args.registry).read_text())
    if isinstance(registry, dict):
        raw = registry["candidates"]
        fallback_family = registry.get("family_id", "UNDECLARED_FAMILY")
    elif isinstance(registry, list):
        raw, fallback_family = registry, "UNDECLARED_FAMILY"
    else:
        raise ValueError("registry must be object or list")
    configs = [{"candidate_id":c["candidate_id"], "family_id":c.get("family_id", fallback_family),
                "direction":c.get("direction", "normal"), "sl_ticks":c["sl_ticks"], "tp_ticks":c["tp_ticks"]} for c in raw]
    runner = FunnelRunner(trade_dates=trade_dates, signal_idx=load("signal_bar_idx"),
                          signal_dir=load("signal_dir"), high=load("high_ticks"), low=load("low_ticks"),
                          bid_open=load("bid_open_ticks"), ask_open=load("ask_open_ticks"),
                          configs=configs, out_dir=args.out, backend="cpu", frozen_split=frozen)
    print(json.dumps(runner.run_e1_e3(max_hold_bars=args.max_hold_bars,
                                     max_matrix_bytes=args.max_matrix_bytes), indent=2, allow_nan=False))

if __name__ == "__main__":
    main()
