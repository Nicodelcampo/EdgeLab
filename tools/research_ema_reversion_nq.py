#!/usr/bin/env python3
"""
tools/research_ema_reversion_nq.py

Estudio empirico de Reversion a la EMA tras Sobre-Extension y Climax HFT.
Evalua la hipotesis de reversión elástica sobre NQ 06-26 (25-tick bars):
  1. Distancia de Sobre-Extensión: |P - EMA| >= K ticks/pts.
  2. Ráfaga HFT en dirección de alejamiento (Climax/Exhaustion).
  3. Rechazo / Reversión instantánea que atrapa al flujo agresivo.
  4. Recorrido elástico hacia la EMA como target dinámico.
"""

import json
import sys
from pathlib import Path
import numpy as np

BUNDLE_PATH = Path("viewer/nt8_bridge/bundles/NQ_0626.json")


def load_bundle():
    if not BUNDLE_PATH.exists():
        print(f"Error: Bundle no encontrado en {BUNDLE_PATH}")
        sys.exit(1)
    with open(BUNDLE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def calc_ema(arr, span):
    alpha = 2.0 / (span + 1.0)
    ema = np.empty_like(arr)
    ema[0] = arr[0]
    for i in range(1, len(arr)):
        ema[i] = alpha * arr[i] + (1 - alpha) * ema[i - 1]
    return ema


def run_ema_study():
    data = load_bundle()
    candles = data["bar_series"]["tick_25"]["candles"]
    zones = data["runs"][0]["zones"]
    meta = data.get("meta", {})
    tick_size = meta.get("tick_size", 0.25)
    n_candles = len(candles)

    c_close = np.array([c["close"] for c in candles], dtype=np.float64)
    c_high = np.array([c["high"] for c in candles], dtype=np.float64)
    c_low = np.array([c["low"] for c in candles], dtype=np.float64)

    print("=== REVERSION A LA EMA TRAS CLIMAX HFT EN NQ 06-26 ===")
    print(f"Activo: {meta.get('contract', 'NQ')} | Velas 25t: {n_candles:,} | Zonas: {len(zones):,}")
    print(f"Tick Size: {tick_size} pts\n")

    ema200 = calc_ema(c_close, 200)
    dist200 = c_close - ema200
    horizons = [10, 25, 50, 100]

    print("========================================================")
    print("ESTRATIFICACION POR DISTANCIA A LA EMA 200 (|P - EMA| >= K)")
    print("========================================================")
    print(f"{'Distancia Min':<14} | {'N Eventos':<9} | {'H=10 Ret':<9} | {'H=25 Ret':<9} | {'H=50 Ret':<9} | {'MFE/MAE (50)':<12} | {'Toca EMA'}")
    print("-" * 88)

    for d_min in [0.0, 10.0, 20.0, 30.0, 40.0]:
        results = []
        for z in zones:
            kind = z.get("kind", "")
            i0 = z.get("start_bar_idx")
            if i0 is None or i0 < 200 or i0 >= n_candles - 110:
                continue
            d = dist200[i0]
            if abs(d) < d_min:
                continue

            if "SELL" in kind and d < 0:
                rev_dir = 1.0
                instant_reversal = (c_close[i0 + 1] > z["top"] or (i0 + 2 < n_candles and c_close[i0 + 2] > z["top"]))
            elif "BUY" in kind and d > 0:
                rev_dir = -1.0
                instant_reversal = (c_close[i0 + 1] < z["bottom"] or (i0 + 2 < n_candles and c_close[i0 + 2] < z["bottom"]))
            else:
                continue

            if not instant_reversal:
                continue

            entry_idx = i0 + 2
            entry_p = c_close[entry_idx]
            sub_high = c_high[entry_idx : entry_idx + 101]
            sub_low = c_low[entry_idx : entry_idx + 101]

            e_data = {"rets": {}, "mfes": {}, "maes": {}}
            for h in horizons:
                e_high = c_high[entry_idx : entry_idx + h + 1]
                e_low = c_low[entry_idx : entry_idx + h + 1]
                mfe = np.max(e_high) - entry_p if rev_dir == 1.0 else entry_p - np.min(e_low)
                mae = entry_p - np.min(e_low) if rev_dir == 1.0 else np.max(e_high) - entry_p
                ret = (c_close[entry_idx + h] - entry_p) * rev_dir
                e_data["rets"][h] = ret
                e_data["mfes"][h] = mfe
                e_data["maes"][h] = mae

            if rev_dir == 1.0:
                hits_ema = np.any(sub_high >= ema200[entry_idx : entry_idx + 101])
            else:
                hits_ema = np.any(sub_low <= ema200[entry_idx : entry_idx + 101])
            e_data["hits_ema"] = hits_ema

            results.append(e_data)

        if results:
            r10 = np.mean([e["rets"][10] for e in results])
            r25 = np.mean([e["rets"][25] for e in results])
            r50 = np.mean([e["rets"][50] for e in results])
            mfe50 = np.median([e["mfes"][50] for e in results])
            mae50 = np.median([e["maes"][50] for e in results])
            ratio50 = mfe50 / max(1e-4, mae50)
            hits = np.mean([e["hits_ema"] for e in results]) * 100.0

            print(f">= {d_min:4.1f} pt ({d_min*4:3.0f}t) | {len(results):<9d} | {r10:+6.2f} pt | {r25:+6.2f} pt | {r50:+6.2f} pt | {ratio50:6.2f}x       | {hits:5.1f}%")


if __name__ == "__main__":
    run_ema_study()
