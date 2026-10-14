# -*- coding: utf-8 -*-
"""Summarize P2-B GC Economic Gate Results Table."""
import json
from pathlib import Path

res_path = Path(r"E:\DatosNT8\bt2a_p2b_gc_economic_run\bt2a_p2b_gc_economic_result.json")
data = json.loads(res_path.read_text(encoding="utf-8"))

print(f"Classification: {data['classification']}")
print(f"Status: {data['status']}")
print(f"Sessions: {data['n_sessions']}")
print(f"Robust Cells: {data['robust_cells']}")
print(f"Base-Only Cells: {data['base_only_cells']}\n")

for scenario in ("base", "adverse"):
    sc_name = "BASE SCENARIO (Friction 3.5t / $35.00)" if scenario == "base" else "ADVERSE SCENARIO (Friction 5.5t / $55.00)"
    print(f"=== {sc_name} ===")
    print(f"{'Barrier':>7} | {'Horizon':>7} | {'Trades':>6} | {'Net USD/Signal':>15} | {'95% CI':>24} | {'p (Holm-16)':>11} | {'P2-A Pos?':>9} | {'Supported?':>10}")
    print("-" * 105)
    for c in data["family"]:
        if c["scenario"] != scenario:
            continue
        est = c["net_usd_per_eligible_signal_equal_session"]
        p2a = "YES" if c["p2a_positive_annotation"] else "no"
        supp = "YES" if c["supported"] else "NO"
        ci_str = f"[${est['lower_95']:6.2f}, ${est['upper_95']:6.2f}]"
        print(f"{c['barrier_ticks']:7d} | {c['horizon_ticks']:7d} | {c['n_trades']:6d} | ${est['point']:14.2f} | {ci_str:>24} | {est['p_holm_16']:11.4f} | {p2a:>9} | {supp:>10}")
    print()
