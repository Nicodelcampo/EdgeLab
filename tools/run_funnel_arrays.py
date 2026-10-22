#!/usr/bin/env python3
"""CPU exploratory outcome runner with a supplied frozen split (+ optional EF0 custody and E4 multiplicity).

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
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--holdout-first-date", type=int, default=None, help="abort if any trade date is >= this value")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--trial-registry", default=None, help="hash-chained global trial counter (required for --e4)")
    parser.add_argument("--seen-ledger", default=None)
    parser.add_argument("--e4", action="store_true", help="also run EF3/EF4: max-null under randomized direction, plateau, global trial count")
    cost = parser.add_mutually_exclusive_group(required=True)
    cost.add_argument("--instrumento", help="toma el costo canónico (edgelab/costos.py, escenario base, sin spread: el kernel entra contra bid/ask)")
    cost.add_argument("--fees-ticks", type=float, help="costo RT explícito en ticks DEL instrumento (declarar la fuente con --cost-source)")
    parser.add_argument("--cost-source", default=None, help="de dónde sale el costo explícito (documento/medición)")
    parser.add_argument("--nsims", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261004)
    args = parser.parse_args()
    if args.instrumento:
        from edgelab import costos
        args.fees_ticks = costos.friccion_rt_ticks(args.instrumento, "base", incluye_spread=False)
        args.cost_source = f"edgelab.costos {costos.tabla()['schema']} {args.instrumento} base sin spread"
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
                          configs=configs, out_dir=args.out, backend="cpu", frozen_split=frozen,
                          holdout_first_date=args.holdout_first_date, campaign_id=args.campaign_id,
                          trial_registry=args.trial_registry, seen_ledger=args.seen_ledger,
                          fees_ticks=args.fees_ticks, cost_source=args.cost_source)
    print(json.dumps(runner.run_e1_e3(min_trades=args.min_trades, max_hold_bars=args.max_hold_bars,
                                     max_matrix_bytes=args.max_matrix_bytes), indent=2, allow_nan=False))
    if args.e4:
        print(json.dumps(runner.run_e4(n_sims=args.nsims, seed=args.seed, min_trades=args.min_trades,
                                       max_hold_bars=args.max_hold_bars, max_matrix_bytes=args.max_matrix_bytes), indent=2, default=str))

if __name__ == "__main__":
    main()
