# -*- coding: utf-8 -*-
"""Detailed Gross vs Friction Decomposition Table."""
import glob
import json
from pathlib import Path

files = sorted(glob.glob(r"E:\DatosNT8\bt2a_p2b_gc_economic_run\checkpoints\session_*.json"))

cells = {}
for f in files:
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    for c in d["cells"]:
        if c["scenario"] != "base":
            continue
        k = (c["barrier_ticks"], c["horizon_ticks"])
        if k not in cells:
            cells[k] = {
                "trades": 0,
                "net_usd": 0.0,
                "target": 0,
                "stop": 0,
                "timeout": 0,
                "stop_ambiguous": 0,
            }
        cells[k]["trades"] += c["n_trades"]
        cells[k]["net_usd"] += c["net_usd"]
        reasons = c.get("exit_reasons", {})
        cells[k]["target"] += reasons.get("target", 0)
        cells[k]["stop"] += reasons.get("stop", 0)
        cells[k]["timeout"] += reasons.get("timeout", 0)
        cells[k]["stop_ambiguous"] += reasons.get("stop_ambiguous", 0)

print(f"{'B':>3} | {'H':>4} | {'Trades':>6} | {'Target %':>9} | {'Stop %':>8} | {'Timeout %':>10} | {'Gross $/tr':>11} | {'Gross ticks':>12} | {'Cost $/tr':>10} | {'Net $/tr':>9} | {'Impacto Costos':>18}")
print("-" * 115)

for (b, h), v in sorted(cells.items()):
    n = v["trades"]
    net_per_tr = v["net_usd"] / n
    cost_per_tr = 35.00
    gross_per_tr = net_per_tr + cost_per_tr
    gross_ticks = gross_per_tr / 10.0
    
    tgt_pct = v["target"] / n * 100
    stp_pct = (v["stop"] + v["stop_ambiguous"]) / n * 100
    tmo_pct = v["timeout"] / n * 100
    
    # Impacto de costos
    if gross_per_tr > 0:
        impact = f"Costos = {cost_per_tr / gross_per_tr * 100:.0f}% del bruto (+)"
    else:
        impact = f"Bruto ya negativo (${gross_per_tr:.2f})"
        
    print(f"{b:3d} | {h:4d} | {n:6d} | {tgt_pct:8.1f}% | {stp_pct:7.1f}% | {tmo_pct:9.1f}% | ${gross_per_tr:10.2f} | {gross_ticks:11.2f}t | ${cost_per_tr:9.2f} | ${net_per_tr:8.2f} | {impact:>25}")
