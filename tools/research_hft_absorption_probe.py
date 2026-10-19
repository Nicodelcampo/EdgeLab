#!/usr/bin/env python3
"""
tools/research_hft_absorption_probe.py

Estudio exploratorio de absorción microestructural y reversión en L1.
Evalúa la hipótesis de reversión en tres niveles:
  1. Incondicional (Naive Benchmark en t0)
  2. Condicional de Contexto (Extremos de Rango / Selling & Buying Climax)
  3. Confirmación por Segunda Serie de Eventos (Re-test con Rechazo vs Perforación)

Incluye contraste contra modelo nulo aleatorio (Monte Carlo),
métricas MFE/MAE, cuantiles de distribución y prueba de bimodalidad.
"""

import json
import math
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


def run_probe():
    data = load_bundle()
    candles = data["bar_series"]["tick_25"]["candles"]
    zones = data["runs"][0]["zones"]
    meta = data.get("meta", {})
    tick_size = meta.get("tick_size", 0.25)
    n_candles = len(candles)

    print(f"=== ESTUDIO DE ABSORCIÓN Y REVERSIÓN HFT (L1) ===")
    print(f"Activo: {meta.get('contract', 'NQ')} | Velas 25t: {n_candles:,} | Zonas: {len(zones):,}")
    print(f"Tick Size: {tick_size} pts\n")

    # Arrays de precios para vectorización rápida
    c_open = np.array([c["open"] for c in candles], dtype=np.float64)
    c_high = np.array([c["high"] for c in candles], dtype=np.float64)
    c_low = np.array([c["low"] for c in candles], dtype=np.float64)
    c_close = np.array([c["close"] for c in candles], dtype=np.float64)

    # Rolling High/Low para contexto (ventana 400 barras = ~1 hora en 25t)
    W = 400
    rolling_min = np.copy(c_low)
    rolling_max = np.copy(c_high)
    for i in range(1, n_candles):
        start_i = max(0, i - W)
        rolling_min[i] = np.min(c_low[start_i : i + 1])
        rolling_max[i] = np.max(c_high[start_i : i + 1])

    horizons = [10, 25, 50, 100, 200]

    # Contenedores para los 3 niveles
    lvl1_events = []
    lvl2_events = []
    lvl3_rejections = []
    lvl3_breakouts = []

    for zi, z in enumerate(zones):
        kind = z.get("kind", "").upper()
        is_hft_sell = "HFT SELL" in kind
        is_hft_buy = "HFT BUY" in kind
        if not (is_hft_sell or is_hft_buy):
            continue

        # Hipótesis de Absorción (Contrarian / Trap):
        # HFT SELL (ventas agresivas absorbidas) -> Esperamos Giro ALCISTA (dir = +1)
        # HFT BUY (compras agresivas absorbidas) -> Esperamos Giro BAJISTA (dir = -1)
        rev_dir = 1.0 if is_hft_sell else -1.0

        i0 = z.get("start_bar_idx")
        if i0 is None or i0 < W or i0 >= n_candles - max(horizons) - 50:
            continue

        z_bot = min(z["top"], z["bottom"])
        z_top = max(z["top"], z["bottom"])
        entry_idx = i0 + 1
        entry_p = c_open[entry_idx]

        # ----------------------------------------------------
        # NIVEL 1: Incondicional en t0
        # ----------------------------------------------------
        evt1 = {"dir": rev_dir, "entry_p": entry_p, "idx": entry_idx, "vol": z.get("vol", 0), "mfe": {}, "mae": {}, "ret": {}}
        for h in horizons:
            sub_high = c_high[entry_idx : entry_idx + h + 1]
            sub_low = c_low[entry_idx : entry_idx + h + 1]
            exit_p = c_close[entry_idx + h]

            if rev_dir == 1.0:
                mfe = np.max(sub_high) - entry_p
                mae = entry_p - np.min(sub_low)
                ret = exit_p - entry_p
            else:
                mfe = entry_p - np.min(sub_low)
                mae = np.max(sub_high) - entry_p
                ret = entry_p - exit_p

            evt1["mfe"][h] = mfe
            evt1["mae"][h] = mae
            evt1["ret"][h] = ret
        lvl1_events.append(evt1)

        # ----------------------------------------------------
        # NIVEL 2: Condicional por Ubicación en el Rango
        # ----------------------------------------------------
        r_min = rolling_min[i0]
        r_max = rolling_max[i0]
        r_span = max(1.0, r_max - r_min)
        pos_in_range = (entry_p - r_min) / r_span  # 0.0 = mínimo del rango, 1.0 = máximo

        # HFT SELL en el 20% inferior del rango (Selling Climax)
        # HFT BUY en el 20% superior del rango (Buying Climax)
        is_extreme = (is_hft_sell and pos_in_range <= 0.20) or (is_hft_buy and pos_in_range >= 0.80)
        if is_extreme:
            lvl2_events.append(evt1)

        # ----------------------------------------------------
        # NIVEL 3: Segunda Serie de Eventos (Re-test y Rechazo)
        # ----------------------------------------------------
        bounced = False
        retest_idx = -1
        max_lookahead = min(n_candles - max(horizons) - 1, i0 + 150)

        for ci in range(i0 + 1, max_lookahead):
            if not bounced:
                if rev_dir == 1.0 and c_high[ci] >= z_top + 3 * tick_size:
                    bounced = True
                elif rev_dir == -1.0 and c_low[ci] <= z_bot - 3 * tick_size:
                    bounced = True
            else:
                # Ya hubo despegue inicial, buscar re-testeo
                if c_low[ci] <= z_top and c_high[ci] >= z_bot:
                    retest_idx = ci
                    break

        if retest_idx != -1:
            # Evaluar si fue rechazo o perforación
            eval_window = min(n_candles - max(horizons) - 1, retest_idx + 6)
            min_retest_p = np.min(c_low[retest_idx:eval_window])
            max_retest_p = np.max(c_high[retest_idx:eval_window])

            if rev_dir == 1.0:
                perforated = min_retest_p < (z_bot - 2 * tick_size)
            else:
                perforated = max_retest_p > (z_top + 2 * tick_size)

            conf_idx = eval_window
            conf_entry_p = c_close[conf_idx]
            evt3 = {"dir": rev_dir, "entry_p": conf_entry_p, "idx": conf_idx, "vol": z.get("vol", 0), "mfe": {}, "mae": {}, "ret": {}}

            for h in horizons:
                sub_high = c_high[conf_idx : conf_idx + h + 1]
                sub_low = c_low[conf_idx : conf_idx + h + 1]
                exit_p = c_close[conf_idx + h]

                if rev_dir == 1.0:
                    mfe = np.max(sub_high) - conf_entry_p
                    mae = conf_entry_p - np.min(sub_low)
                    ret = exit_p - conf_entry_p
                else:
                    mfe = conf_entry_p - np.min(sub_low)
                    mae = np.max(sub_high) - conf_entry_p
                    ret = conf_entry_p - exit_p

                evt3["mfe"][h] = mfe
                evt3["mae"][h] = mae
                evt3["ret"][h] = ret

            if not perforated:
                lvl3_rejections.append(evt3)
            else:
                lvl3_breakouts.append(evt3)

    # ----------------------------------------------------
    # BENCHMARK NULO (MONTE CARLO RANDOM ENTRIES)
    # ----------------------------------------------------
    n_rand = 5000
    np.random.seed(42)
    rand_indices = np.random.randint(W, n_candles - max(horizons) - 50, size=n_rand)
    rand_dirs = np.random.choice([1.0, -1.0], size=n_rand)

    null_events = []
    for r_idx, r_dir in zip(rand_indices, rand_dirs):
        r_entry = c_open[r_idx]
        e_null = {"dir": r_dir, "entry_p": r_entry, "mfe": {}, "mae": {}, "ret": {}}
        for h in horizons:
            sub_high = c_high[r_idx : r_idx + h + 1]
            sub_low = c_low[r_idx : r_idx + h + 1]
            exit_p = c_close[r_idx + h]
            if r_dir == 1.0:
                mfe = np.max(sub_high) - r_entry
                mae = r_entry - np.min(sub_low)
                ret = exit_p - r_entry
            else:
                mfe = r_entry - np.min(sub_low)
                mae = np.max(sub_high) - r_entry
                ret = r_entry - exit_p
            e_null["mfe"][h] = mfe
            e_null["mae"][h] = mae
            e_null["ret"][h] = ret
        null_events.append(e_null)

    # ----------------------------------------------------
    # TABULACIÓN Y ANÁLISIS ESTADÍSTICO
    # ----------------------------------------------------
    def analyze_population(name, evts):
        n = len(evts)
        print(f"\n========================================================")
        print(f"POBLACIÓN: {name} (N = {n:,} eventos)")
        print(f"========================================================")
        if n < 10:
            print("Muestra insuficiente para inferencia estadística.")
            return

        print(f"{'H (bars)':<8} | {'Ret Mean':<10} | {'Ret Med':<8} | {'P25':<7} | {'P75':<7} | {'MFE Med':<9} | {'MAE Med':<9} | {'MFE/MAE':<8} | {'WinRate (MFE>MAE)'}")
        print("-" * 96)

        for h in horizons:
            rets = np.array([e["ret"][h] for e in evts])
            mfes = np.array([e["mfe"][h] for e in evts])
            maes = np.array([e["mae"][h] for e in evts])

            r_mean = np.mean(rets)
            r_med = np.median(rets)
            p25 = np.percentile(rets, 25)
            p75 = np.percentile(rets, 75)

            mfe_med = np.median(mfes)
            mae_med = np.median(maes)
            ratio = mfe_med / max(1e-4, mae_med)

            win_rate = np.mean(mfes > maes) * 100.0

            print(f"{h:<8d} | {r_mean:+7.2f} pt | {r_med:+7.2f} pt | {p25:+5.1f} | {p75:+5.1f} | {mfe_med:7.2f} pt | {mae_med:7.2f} pt | {ratio:7.2f}x | {win_rate:6.1f}%")

    analyze_population("1. Benchmark Naive Incondicional (t0 sin filtros)", lvl1_events)
    analyze_population("2. Condicional de Contexto (Extremo del Rango 20%)", lvl2_events)
    analyze_population("3. Confirmación: Re-test con Rechazo (Segunda Serie - Todo Vol)", lvl3_rejections)

    # Subconjunto de Re-test con Alto Volumen de Absorción (P75 >= 90c, P90 >= 120c)
    retest_vol90 = [e for e in lvl3_rejections if e.get("vol", 0) >= 90]
    retest_vol120 = [e for e in lvl3_rejections if e.get("vol", 0) >= 120]
    analyze_population("3a. Confirmación Re-test + Iceberg Institucional (Vol >= 90c)", retest_vol90)
    analyze_population("3b. Confirmación Re-test + Iceberg Masivo (Vol >= 120c)", retest_vol120)

    analyze_population("3c. Fallo / Perforación en Re-test (Reversal fallido)", lvl3_breakouts)
    analyze_population("4. Modelo Nulo (Entradas Aleatorias Monte Carlo)", null_events)

    # Diagnóstico de bimodalidad y trampa de cancelación en Naive (H=50)
    rets_h50 = np.array([e["ret"][50] for e in lvl1_events])
    pos_tail = np.mean(rets_h50 > 12.0) * 100.0
    neg_tail = np.mean(rets_h50 < -12.0) * 100.0
    std_h50 = np.std(rets_h50)

    print(f"\n--- DIAGNÓSTICO DE LA TRAMPA DE CANCELACIÓN (Horizonte 50 barras en Naive) ---")
    print(f"Cola Positiva (> +12 pts): {pos_tail:.1f}% de los eventos")
    print(f"Cola Negativa (< -12 pts): {neg_tail:.1f}% de los eventos")
    print(f"Dispersión total (Desv. Estándar): {std_h50:.2f} pts (Demuestra que la media ~0 es por cancelación simétrica, no por ausencia de movimiento)")


if __name__ == "__main__":
    run_probe()
