# -*- coding: utf-8 -*-
"""Calculate Gross P&L vs Friction Costs Breakdown for P2-B GC."""
import glob
import json
from pathlib import Path

files = sorted(glob.glob(r"E:\DatosNT8\bt2a_p2b_gc_economic_run\checkpoints\session_*.json"))
print(f"Loaded {len(files)} session checkpoints.\n")

cells_data = {}

for fpath in files:
    d = json.loads(Path(fpath).read_text(encoding="utf-8"))
    for cell in d["cells"]:
        if cell["scenario"] != "base":
            continue
        b = cell["barrier_ticks"]
        h = cell["horizon_ticks"]
        k = (b, h)
        if k not in cells_data:
            cells_data[k] = {
                "n_trades": 0,
                "gross_usd": 0.0,
                "net_usd": 0.0,
                "gross_winning_usd": 0.0,
                "gross_losing_usd": 0.0,
                "wins": 0,
                "losses": 0,
                "timeouts": 0,
            }
        
        cells_data[k]["n_trades"] += cell["n_trades"]
        cells_data[k]["net_usd"] += cell["net_usd"]
        
        for t in cell.get("trades", []):
            g_usd = t["gross_ticks"] * 10.0
            cells_data[k]["gross_usd"] += g_usd
            if g_usd > 0:
                cells_data[k]["gross_winning_usd"] += g_usd
                cells_data[k]["wins"] += 1
            elif g_usd < 0:
                cells_data[k]["gross_losing_usd"] += g_usd
                cells_data[k]["losses"] += 1
            else:
                cells_data[k]["timeouts"] += 1

print("=" * 115)
print(f"{'B':>3} | {'H':>4} | {'Trades':>6} | {'Gross USD/tr':>13} | {'Cost USD/tr':>12} | {'Net USD/tr':>11} | {'WinRate':>8} | {'Gross P&L Total':>16} | {'Total Cost':>12} | {'Cost / Gross Wins':>18}")
print("=" * 115)

for (b, h), v in sorted(cells_data.items()):
    n = v["n_trades"]
    g_avg = v["gross_usd"] / n if n > 0 else 0.0
    cost_avg = 35.00
    net_avg = v["net_usd"] / n if n > 0 else 0.0
    wr = (v["wins"] / n * 100) if n > 0 else 0.0
    total_cost = cost_avg * n
    cost_over_wins = (total_cost / v["gross_winning_usd"] * 100) if v["gross_winning_usd"] > 0 else 0.0
    
    print(f"{b:3d} | {h:4d} | {n:6d} | ${g_avg:11.2f} | ${cost_avg:10.2f} | ${net_avg:9.2f} | {wr:7.1f}% | ${v['gross_usd']:14.2f} | ${total_cost:10.2f} | {cost_over_wins:16.1f}%")

print("=" * 115)
