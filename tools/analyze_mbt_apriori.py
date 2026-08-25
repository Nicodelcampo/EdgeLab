#!/usr/bin/env python3
"""Análisis a-priori estructural de BigTrap2Absorption sobre MBT.

Evalúa:
1. Cubetas/sesión (residual=False, por td): mediana, p25/p75.
2. Llenado del anillo causal: MinHistoryBuckets in {50, 100, 200}, AbsorptionLookback in {200, 500}.
3. Tasa de eventos vs q in {90, 95, 97.5, 99}: eventos/sesión y % de cubetas.
4. Efecto de MinStackedRows in {1, 2, 3} y MinTrapFrac in {0.1, 0.2, 0.3}.
5. Dependencia de régimen por sesión (td).
6. Regla de decisión pre-registrada y configuración recomendada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd


def percentile(arr: list[float], q: float) -> float:
    n = len(arr)
    if n == 0:
        return float("nan")
    if n == 1:
        return float(arr[0])
    tmp = sorted(arr)
    qq = 0.0 if q < 0.0 else (100.0 if q > 100.0 else float(q))
    pos = (qq / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo < 0:
        lo = 0
    if hi >= n:
        hi = n - 1
    if lo == hi:
        return float(tmp[lo])
    return float(tmp[lo] + (tmp[hi] - tmp[lo]) * (pos - lo))


def parse_kv(text: str) -> dict[str, str]:
    out = {}
    for item in text.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_export(csv_path: Path):
    meta = {}
    bars = []
    scores = []
    traps = []
    zones = []
    fills = []

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# meta"):
                meta_str = line[len("# meta"):].strip()
                for item in meta_str.split(","):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        meta[k.strip()] = v.strip()
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            seq = int(parts[0])
            iso_ts = parts[1]
            ev_type = parts[2]
            payload = parse_kv(parts[3])
            payload["_seq"] = seq
            payload["_iso"] = iso_ts

            if ev_type == "BARRA_PROCESADA":
                bars.append(payload)
            elif ev_type == "ABS_SCORE":
                scores.append(payload)
            elif ev_type == "TRAP":
                traps.append(payload)
            elif ev_type == "ZONE_CREATED":
                zones.append(payload)
            elif ev_type == "FILL":
                fills.append(payload)

    return meta, bars, scores, traps, zones, fills


def analyze_file(csv_path: Path):
    print(f"\n==================================================")
    print(f"[*] Analizando {csv_path.name}...")
    meta, bars, scores, traps, zones, fills = parse_export(csv_path)
    tw = int(meta.get("tape_window", 25))

    # 1. Cubetas por sesion (residual == False)
    scores_non_res = [s for s in scores if s.get("residual") == "False"]
    scores_res = [s for s in scores if s.get("residual") == "True"]

    # Por sesion td
    bkt_by_session = defaultdict(int)
    res_by_session = defaultdict(int)
    for s in scores:
        td = s["td"]
        if s.get("residual") == "False":
            bkt_by_session[td] += 1
        else:
            res_by_session[td] += 1

    all_sessions = sorted(set(s["td"] for s in scores))
    bkt_counts = [bkt_by_session[td] for td in all_sessions if bkt_by_session[td] > 0]
    
    # Separar front month vs pre-roll (umbral natural: >= 1000 ticks o >= 50 cubetas)
    front_sessions = [td for td in all_sessions if bkt_by_session[td] >= 100]
    preroll_sessions = [td for td in all_sessions if 0 < bkt_by_session[td] < 100]

    bkt_counts_front = [bkt_by_session[td] for td in front_sessions]
    bkt_counts_preroll = [bkt_by_session[td] for td in preroll_sessions]

    print(f"  TW = {tw}")
    print(f"  Total cubetas: {len(scores):,} (Completas: {len(scores_non_res):,}, Residuales: {len(scores_res):,})")
    print(f"  Sesiones totales con cubetas: {len(bkt_counts)} (Front-month: {len(front_sessions)}, Pre-roll: {len(preroll_sessions)})")
    if bkt_counts:
        print(f"  Cubetas/sesion global: mediana={np.median(bkt_counts):.1f}, p25={np.percentile(bkt_counts, 25):.1f}, p75={np.percentile(bkt_counts, 75):.1f}, min={np.min(bkt_counts)}, max={np.max(bkt_counts)}")
    if bkt_counts_front:
        print(f"  Cubetas/sesion FRONT MONTH (>=100): mediana={np.median(bkt_counts_front):.1f}, p25={np.percentile(bkt_counts_front, 25):.1f}, p75={np.percentile(bkt_counts_front, 75):.1f}, min={np.min(bkt_counts_front)}, max={np.max(bkt_counts_front)}")

    # 2. Llenado del anillo causal
    # Recomputar streams de umbral causal para combinaciones de (MinHistoryBuckets, AbsorptionLookback)
    a_scores_series = [(int(s["bar"]), s.get("residual") == "True", float(s["a_score"]), s["td"]) for s in scores]
    
    ring_configs = [
        (50, 200),
        (100, 200),
        (200, 200),
        (50, 500),
        (100, 500),
        (200, 500),
    ]

    print(f"\n  --- Llenado del Anillo Causal (Burn-in) ---")
    burnin_results = {}
    for min_hist, lookback in ring_configs:
        ring = []
        ring_cap = lookback
        pos = 0
        count = 0
        ring_buf = [0.0] * ring_cap
        
        first_ready_bar = None
        first_ready_td = None
        first_ready_idx = None
        ready_buckets = 0

        for idx, (bar, res, score, td) in enumerate(a_scores_series):
            if count >= min_hist:
                if first_ready_bar is None:
                    first_ready_bar = bar
                    first_ready_td = td
                    first_ready_idx = idx
                ready_buckets += 1
            if not res:
                ring_buf[pos] = score
                pos = (pos + 1) % ring_cap
                if count < ring_cap:
                    count += 1
        
        burnin_results[(min_hist, lookback)] = {
            "first_ready_bar": first_ready_bar,
            "first_ready_td": first_ready_td,
            "first_ready_idx": first_ready_idx,
            "ready_buckets": ready_buckets,
            "total_buckets": len(a_scores_series),
        }
        print(f"    min_hist={min_hist:3d}, lookback={lookback:3d} -> Activo en bar {first_ready_bar} (td {first_ready_td}), {ready_buckets:,}/{len(a_scores_series):,} cubetas listas ({ready_buckets/len(a_scores_series)*100:.1f}%)")

    # 3. Mapeo de eventos TRAP offline vs q, MinStackedRows, MinTrapFrac
    # Indexar a_scores por bar para recomputar percentil exacto causal
    print(f"\n  --- Barrido Estructural Offline sobre TRAP ---")
    print(f"  Total TRAP brutos exportados: {len(traps):,}")

    q_levels = [90.0, 95.0, 97.5, 99.0]
    min_rows_levels = [1, 2, 3]
    min_frac_levels = [0.10, 0.20, 0.30]

    # Pre-calcular umbrales causales para lookback=500, min_hist=100 (y 200)
    def compute_threshold_map(min_hist, lookback, q):
        thr_by_bar = {}
        ring_cap = lookback
        pos = 0
        count = 0
        ring_buf = [0.0] * ring_cap
        for bar, res, score, td in a_scores_series:
            if count >= min_hist:
                s_arr = ring_buf[:count] if count < ring_cap else ring_buf
                thr_by_bar[bar] = percentile(s_arr, q)
            else:
                thr_by_bar[bar] = float("nan")
            if not res:
                ring_buf[pos] = score
                pos = (pos + 1) % ring_cap
                if count < ring_cap:
                    count += 1
        return thr_by_bar

    # Evaluamos con lookback=500, min_hist=100 (y min_hist=200)
    grid_results = []
    for min_hist in [100, 200]:
        for lookback in [500]:
            for q in q_levels:
                thr_map = compute_threshold_map(min_hist, lookback, q)
                for rows_cut in min_rows_levels:
                    for frac_cut in min_frac_levels:
                        # Filtrar eventos TRAP
                        # Invariantes:
                        # 1. Bar no residual (implícito si a_pass)
                        # 2. a_score >= thr_map[bar]
                        # 3. side_match == True (RequireFlowSideMatch)
                        # 4. run_rows >= rows_cut
                        # 5. run_frac >= frac_cut
                        n_events = 0
                        events_by_session = defaultdict(int)
                        events_by_front = defaultdict(int)

                        for tr in traps:
                            bar = int(tr["bar"])
                            thr = thr_map.get(bar, float("nan"))
                            if math.isnan(thr):
                                continue
                            a_score = float(tr["a_score"])
                            if a_score < thr:
                                continue
                            if tr.get("side_match") != "True":
                                continue
                            run_rows = int(tr.get("run_rows", 0))
                            if run_rows < rows_cut:
                                continue
                            run_frac = float(tr.get("run_frac", 0.0))
                            if run_frac < frac_cut:
                                continue

                            n_events += 1
                            td = tr["td"]
                            events_by_session[td] += 1
                            if td in front_sessions:
                                events_by_front[td] += 1

                        ev_per_front = [events_by_front[td] for td in front_sessions]
                        pct_buckets_front = (n_events / sum(bkt_counts_front) * 100) if sum(bkt_counts_front) else 0.0
                        med_ev_front = np.median(ev_per_front) if ev_per_front else 0.0

                        grid_results.append({
                            "tw": tw,
                            "min_hist": min_hist,
                            "lookback": lookback,
                            "q": q,
                            "min_rows": rows_cut,
                            "min_frac": frac_cut,
                            "n_events": n_events,
                            "pct_buckets_front": pct_buckets_front,
                            "med_ev_front": med_ev_front,
                            "p25_ev_front": np.percentile(ev_per_front, 25) if ev_per_front else 0.0,
                            "p75_ev_front": np.percentile(ev_per_front, 75) if ev_per_front else 0.0,
                        })

    # Mostrar tabla resumen para baseline (MinStackedRows=2, MinTrapFrac=0.20, lookback=500, min_hist=100)
    print(f"\n  --- Tasa de Eventos vs q (MinStackedRows=2, MinTrapFrac=0.20, lookback=500, min_hist=100) ---")
    print(f"  {'q':>6s} | {'Eventos':>8s} | {'% Cubetas (Front)':>18s} | {'Eventos/Ses (Med)':>18s} | {'p25-p75':>12s}")
    print(f"  {'-'*6}-+-{'-'*8}-+-{'-'*18}-+-{'-'*18}-+-{'-'*12}")
    for r in grid_results:
        if r["min_hist"] == 100 and r["lookback"] == 500 and r["min_rows"] == 2 and abs(r["min_frac"] - 0.20) < 1e-4:
            print(f"  {r['q']:6.1f} | {r['n_events']:8d} | {r['pct_buckets_front']:17.2f}% | {r['med_ev_front']:18.1f} | {r['p25_ev_front']:4.1f} - {r['p75_ev_front']:4.1f}")

    # Mostrar efecto de MinStackedRows (1, 2, 3) con q=95, min_frac=0.20
    print(f"\n  --- Sensibilidad MinStackedRows (q=95.0, MinTrapFrac=0.20) ---")
    for r in grid_results:
        if r["min_hist"] == 100 and r["lookback"] == 500 and abs(r["q"] - 95.0) < 1e-4 and abs(r["min_frac"] - 0.20) < 1e-4:
            print(f"    MinStackedRows={r['min_rows']} -> Eventos={r['n_events']}, %Cubetas={r['pct_buckets_front']:.2f}%, Med/Ses={r['med_ev_front']:.1f}")

    # Mostrar efecto de MinTrapFrac (0.10, 0.20, 0.30) con q=95, min_rows=2
    print(f"\n  --- Sensibilidad MinTrapFrac (q=95.0, MinStackedRows=2) ---")
    for r in grid_results:
        if r["min_hist"] == 100 and r["lookback"] == 500 and abs(r["q"] - 95.0) < 1e-4 and r["min_rows"] == 2:
            print(f"    MinTrapFrac={r['min_frac']:.2f} -> Eventos={r['n_events']}, %Cubetas={r['pct_buckets_front']:.2f}%, Med/Ses={r['med_ev_front']:.1f}")

    # 4. Analisis de Regimen por sesion (td)
    # Seleccionar configuracion de referencia: q=95.0, min_rows=2, min_frac=0.20, min_hist=100
    thr_map_ref = compute_threshold_map(100, 500, 95.0)
    ev_by_td = defaultdict(int)
    for tr in traps:
        bar = int(tr["bar"])
        thr = thr_map_ref.get(bar, float("nan"))
        if math.isnan(thr) or float(tr["a_score"]) < thr or tr.get("side_match") != "True":
            continue
        if int(tr.get("run_rows", 0)) < 2 or float(tr.get("run_frac", 0.0)) < 0.20:
            continue
        ev_by_td[tr["td"]] += 1

    print(f"\n  --- Régimen por Sesión (q=95, rows=2, frac=0.20) ---")
    front_counts = [ev_by_td[td] for td in front_sessions]
    if front_counts:
        p10 = np.percentile(front_counts, 10)
        p90 = np.percentile(front_counts, 90)
        p50 = np.median(front_counts)
        ratio_p90_p10 = (p90 / p10) if p10 > 0 else float("inf")
        print(f"  Front month sesiones ({len(front_sessions)}): mediana={p50:.1f}, p10={p10:.1f}, p90={p90:.1f}, max={max(front_counts)}, min={min(front_counts)}")
        print(f"  Ratio p90/p10: {ratio_p90_p10:.2f}x (Umbral de alerta de régimen: >3x)")
        for td in front_sessions[-10:]:
            print(f"    Sesion {td}: {ev_by_td[td]} eventos (de {bkt_by_session[td]} cubetas)")

    return {
        "tw": tw,
        "meta": meta,
        "n_scores": len(scores),
        "n_scores_non_res": len(scores_non_res),
        "n_scores_res": len(scores_res),
        "all_sessions": all_sessions,
        "front_sessions": front_sessions,
        "preroll_sessions": preroll_sessions,
        "bkt_counts_front": bkt_counts_front,
        "bkt_counts_preroll": bkt_counts_preroll,
        "burnin_results": burnin_results,
        "grid_results": grid_results,
        "ev_by_td": dict(ev_by_td),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="E:/DatosNT8/mbt_apriori")
    args = ap.parse_args()

    out_dir = Path(args.dir)
    files = sorted(out_dir.glob("mbt_export__TW*.csv"))
    if not files:
        print(f"No se encontraron exports en {out_dir}")
        return

    results = []
    for f in files:
        res = analyze_file(f)
        results.append(res)


if __name__ == "__main__":
    main()
