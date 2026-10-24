#!/usr/bin/env python3
"""Exploración visual (Fase 1): grilla de 300 combinaciones de SL/TP/BE para escalonadas 150t en GC.

Sin replay tick a tick, sin controles, sin max-T. Simulación sobre velas de 25t (como el visor).
Sirve para descartar rápido y orientar qué correr en serio.

Uso: python tools/luximb_parity/gc_150t_grid_visual.py
"""
import json
import sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]  # E:\EdgeLab-port
VIEW = REPO / "viewer" / "nt8_bridge"

# GC friction from REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md
# spread 3.43 + commission 0.46 + slippage 2.0 = 5.89 ticks
FRICTION_TICKS = 5.89
HORIZON = 1500  # max bars to wait

ASSETS = [
    "GC_12-25_M1_LUXIMB",
    "GC_02-26_M1_LUXIMB",
    "GC_04-26_M1_LUXIMB",
]

SL_MODES = ["ult2", "pri2", "mitad", "30", "60"]
TP_RS = [1, 2, 3, 5, 10]
BE_RS = [0, 1, 2]  # 0 = no BE


def load_bundle_candles(aid):
    path = VIEW / "bundles" / f"{aid}.json"
    b = json.loads(path.read_text(encoding="utf-8"))
    tk = float(b["meta"]["tick_size"])
    cd = b["bar_series"]["tick_25"]["candles"]
    return cd, tk


def load_det(aid):
    path = VIEW / "bundles" / "peaks_det" / f"{aid}__picos150.json"
    return json.loads(path.read_text(encoding="utf-8"))


def sl_ticks_for(z, tkz, mode):
    sd = -1 if z["kind"] == "H" else 1
    if mode == "mitad":
        d = -sd * (z["picos"][0][2] - z["det_precio"]) / 2 / tkz
        return d if d > 0 else float("nan")
    if mode == "pri2":
        d = -sd * 2 * (z["picos"][0][2] - z["det_precio"]) / tkz
        return d if d > 0 else float("nan")
    if mode == "ult2":
        d = -sd * 2 * (z["det_nivel"] - z["det_precio"]) / tkz
        return d if d > 0 else float("nan")
    return float(mode)


def sim_one(z, cd, tkz, sl_mode, tp_r, be_r):
    if z.get("det_i") is None:
        return None
    sz = sl_ticks_for(z, tkz, sl_mode)
    if not (sz > 0):
        return None

    sd = -1 if z["kind"] == "H" else 1
    en = z["det_precio"]
    slP = en - sd * sz * tkz
    tpP = en + sd * sz * tp_r * tkz
    beP = en + sd * sz * be_r * tkz if be_r > 0 else None

    i0 = (z["i25_post"] - 1) if z.get("i25_post") is not None else z["det_i"]
    ex = None
    why = "fin"
    stp = slP
    be_on = False

    for kk in range(i0 + 1, min(len(cd), i0 + HORIZON)):
        bb = cd[kk]
        hitS = bb["high"] >= stp if sd == -1 else bb["low"] <= stp
        hitT = bb["low"] <= tpP if sd == -1 else bb["high"] >= tpP

        if hitS:
            ex = kk
            why = "BE" if be_on else "SL"
            break
        if hitT:
            ex = kk
            why = "TP"
            break
        if beP is not None and not be_on:
            hitBE = bb["low"] <= beP if sd == -1 else bb["high"] >= beP
            if hitBE:
                be_on = True
                stp = en

    if ex is None:
        ex = min(len(cd) - 1, i0 + HORIZON)

    if why == "TP":
        r = tp_r
    elif why == "SL":
        r = -1.0
    elif why == "BE":
        r = 0.0
    else:
        r = ((cd[ex]["close"] - en) * sd) / (sz * tkz)

    return dict(r=r, why=why, sl_ticks=sz, sl_pts=sz * tkz)


def run_grid():
    all_results = []

    for aid in ASSETS:
        print(f"Loading {aid}...", flush=True)
        cd, tkz = load_bundle_candles(aid)
        det = load_det(aid)
        print(f"  {len(cd)} candles, {len(det['zonas'])} detections, tkz={tkz}")

        for sl_mode in SL_MODES:
            for tp_r in TP_RS:
                for be_r in BE_RS:
                    if be_r > 0 and tp_r <= be_r:
                        continue

                    R = []
                    sl_ticks_all = []
                    st = {"TP": 0, "SL": 0, "BE": 0, "fin": 0}

                    for z in det["zonas"]:
                        res = sim_one(z, cd, tkz, sl_mode, tp_r, be_r)
                        if res is None:
                            continue
                        R.append(res["r"])
                        sl_ticks_all.append(res["sl_ticks"])
                        st[res["why"]] += 1

                    n = len(R)
                    if n == 0:
                        continue

                    tot_r = sum(R)
                    win = sum(1 for x in R if x > 0)
                    sl_med = float(np.median(sl_ticks_all))
                    sl_pts_med = sl_med * tkz
                    r_per_op = tot_r / n
                    cost_in_r = FRICTION_TICKS / sl_med if sl_med > 0 else 99
                    r_neto = r_per_op - cost_in_r

                    all_results.append(dict(
                        asset=aid, sl=sl_mode, tp=tp_r, be=be_r,
                        n=n, win_pct=round(100 * win / n, 1),
                        tp_n=st["TP"], sl_n=st["SL"], be_n=st["BE"], fin_n=st["fin"],
                        r_per_op=round(r_per_op, 4),
                        sl_med_ticks=round(sl_med, 1),
                        sl_med_pts=round(sl_pts_med, 2),
                        cost_r=round(cost_in_r, 4),
                        r_neto=round(r_neto, 4),
                    ))

    # Sort by neto descending
    all_results.sort(key=lambda x: -x["r_neto"])

    # Output
    out_path = REPO / "docs" / "research" / "eurusd_escalonadas_20261021" / "gc_150t_grid_visual.json"
    out_path.write_text(json.dumps(all_results, indent=1), encoding="utf-8")

    # Print top and bottom
    print(f"\n{'='*120}")
    print(f"Total cells evaluated: {len(all_results)}")
    print(f"\nTOP 30 by R neto (after ~5.89 ticks friction):")
    print(f"{'Asset':<25} {'SL':<8} {'TP':>4} {'BE':>3} {'N':>6} {'Win%':>6} {'TP':>4} {'SL':>4} {'BE':>4} {'fin':>4} {'R/op':>8} {'SL_med':>7} {'Cost_R':>7} {'R_neto':>8}")
    print("-" * 120)
    for r in all_results[:30]:
        print(f"{r['asset']:<25} {r['sl']:<8} {r['tp']:>4}R {r['be']:>2}R {r['n']:>6} {r['win_pct']:>5.1f}% {r['tp_n']:>4} {r['sl_n']:>4} {r['be_n']:>4} {r['fin_n']:>4} {r['r_per_op']:>+8.4f} {r['sl_med_ticks']:>6.1f}t {r['cost_r']:>7.4f} {r['r_neto']:>+8.4f}")

    print(f"\nBOTTOM 10:")
    for r in all_results[-10:]:
        print(f"{r['asset']:<25} {r['sl']:<8} {r['tp']:>4}R {r['be']:>2}R {r['n']:>6} {r['win_pct']:>5.1f}% {r['tp_n']:>4} {r['sl_n']:>4} {r['be_n']:>4} {r['fin_n']:>4} {r['r_per_op']:>+8.4f} {r['sl_med_ticks']:>6.1f}t {r['cost_r']:>7.4f} {r['r_neto']:>+8.4f}")

    # Summary by SL mode
    print(f"\n{'='*80}")
    print("RESUMEN POR MODO DE SL (promedio ponderado por N):")
    for sl_mode in SL_MODES:
        cells = [r for r in all_results if r["sl"] == sl_mode]
        if not cells:
            continue
        total_n = sum(c["n"] for c in cells)
        avg_r = sum(c["r_per_op"] * c["n"] for c in cells) / total_n
        avg_neto = sum(c["r_neto"] * c["n"] for c in cells) / total_n
        avg_sl = sum(c["sl_med_ticks"] * c["n"] for c in cells) / total_n
        pos = sum(1 for c in cells if c["r_neto"] > 0)
        print(f"  SL={sl_mode:<8}: {len(cells):>3} celdas, SL med {avg_sl:>6.1f}t, R/op bruto {avg_r:>+.4f}, R/op neto {avg_neto:>+.4f}, positivas {pos}/{len(cells)}")

    # Summary by asset
    print(f"\nRESUMEN POR CONTRATO:")
    for aid in ASSETS:
        cells = [r for r in all_results if r["asset"] == aid]
        if not cells:
            continue
        total_n = sum(c["n"] for c in cells)
        avg_neto = sum(c["r_neto"] * c["n"] for c in cells) / total_n
        pos = sum(1 for c in cells if c["r_neto"] > 0)
        print(f"  {aid}: {len(cells)} celdas, {total_n} ops total, R neto promedio {avg_neto:>+.4f}, positivas {pos}/{len(cells)}")

    # Cells that survive both bruto > 0 AND neto > 0
    survivors = [r for r in all_results if r["r_neto"] > 0 and r["n"] >= 30]
    print(f"\n{'='*80}")
    print(f"SOBREVIVIENTES (R neto > 0 Y N >= 30): {len(survivors)}")
    for r in survivors[:20]:
        print(f"  {r['asset']:<25} SL={r['sl']:<8} TP={r['tp']}R BE={r['be']}R  N={r['n']}  win={r['win_pct']}%  R/op={r['r_per_op']:+.4f}  cost={r['cost_r']:.4f}  neto={r['r_neto']:+.4f}  SL_med={r['sl_med_pts']:.2f}pts")


if __name__ == "__main__":
    run_grid()
