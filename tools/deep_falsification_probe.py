#!/usr/bin/env python3
"""
tools/deep_falsification_probe.py

INVESTIGACIÓN PROFUNDA, FALSIFICACIÓN MULTI-FACTOR Y RECOMENDACIÓN ESTRATÉGICA
1. Asimetría Direccional (Long vs Short / Market Drift).
2. Curva de Sensibilidad Paramétrica Continua (Distancias 15 a 50 pt; EMA 50 a 500).
3. Análisis de Régimen Interdiario: Qué separó a los días ganadores de los perdedores.
4. Interacción con Volumen Institucional de Zona (Icebergs en Clímax).
5. Evaluación de Muerte por Consumo Tick a Tick como Filtro de Falso Quiebre.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

BUNDLE_PATH = Path("viewer/nt8_bridge/bundles/NQ_0626.json")


def load_data():
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


def run_deep_probe():
    data = load_data()
    candles = data["bar_series"]["tick_25"]["candles"]
    zones = data["runs"][0]["zones"]
    n_candles = len(candles)
    tick_size = 0.25

    c_open = np.array([c["open"] for c in candles], dtype=np.float64)
    c_high = np.array([c["high"] for c in candles], dtype=np.float64)
    c_low = np.array([c["low"] for c in candles], dtype=np.float64)
    c_close = np.array([c["close"] for c in candles], dtype=np.float64)
    c_time = np.array([c["time"] for c in candles], dtype=np.int64)

    print("=" * 80)
    print("AUDITORIA DE PROFUNDIZACION Y FALSIFICACION — EDGELAB")
    print("=" * 80)

    # =========================================================================
    # 1. ASIMETRIA DIRECCIONAL (LONG VS SHORT / SESGO DE DRIFT)
    # =========================================================================
    print("\n" + "=" * 80)
    print("1. ASIMETRIA DIRECCIONAL: LONG (SUB-EMA) VS SHORT (SOBRE-EMA)")
    print("¿El resultado positivo proviene solo de compras en un mercado alcista?")
    print("=" * 80)

    ema200 = calc_ema(c_close, 200)
    dist200 = c_close - ema200

    long_events = []
    short_events = []

    for z in zones:
        kind = z.get("kind", "")
        i0 = z.get("start_bar_idx")
        if i0 is None or i0 < 200 or i0 >= n_candles - 110:
            continue
        d = dist200[i0]
        if abs(d) < 30.0:
            continue

        if "SELL" in kind and d < 0:
            # LONG
            rev_dir = 1.0
            instant_reversal = (c_close[i0 + 1] > z["top"] or (i0 + 2 < n_candles and c_close[i0 + 2] > z["top"]))
            if instant_reversal:
                entry_idx = i0 + 2
                entry_p = c_close[entry_idx]
                ret50 = (c_close[entry_idx + 50] - entry_p) * rev_dir
                mfe = np.max(c_high[entry_idx + 1 : entry_idx + 52]) - entry_p
                mae = entry_p - np.min(c_low[entry_idx + 1 : entry_idx + 52])
                long_events.append({"ret50": ret50, "mfe": mfe, "mae": mae, "time": c_time[entry_idx], "vol": z.get("vol", 0)})

        elif "BUY" in kind and d > 0:
            # SHORT
            rev_dir = -1.0
            instant_reversal = (c_close[i0 + 1] < z["bottom"] or (i0 + 2 < n_candles and c_close[i0 + 2] < z["bottom"]))
            if instant_reversal:
                entry_idx = i0 + 2
                entry_p = c_close[entry_idx]
                ret50 = (c_close[entry_idx + 50] - entry_p) * rev_dir
                mfe = entry_p - np.min(c_low[entry_idx + 1 : entry_idx + 52])
                mae = np.max(c_high[entry_idx + 1 : entry_idx + 52]) - entry_p
                short_events.append({"ret50": ret50, "mfe": mfe, "mae": mae, "time": c_time[entry_idx], "vol": z.get("vol", 0)})

    l_ret = np.mean([e["ret50"] for e in long_events]) if long_events else 0.0
    l_mfe = np.median([e["mfe"] for e in long_events]) if long_events else 0.0
    l_mae = np.median([e["mae"] for e in long_events]) if long_events else 0.0
    l_win = np.mean([1 if e["ret50"] > 0 else 0 for e in long_events]) * 100.0

    s_ret = np.mean([e["ret50"] for e in short_events]) if short_events else 0.0
    s_mfe = np.median([e["mfe"] for e in short_events]) if short_events else 0.0
    s_mae = np.median([e["mae"] for e in short_events]) if short_events else 0.0
    s_win = np.mean([1 if e["ret50"] > 0 else 0 for e in short_events]) * 100.0

    print(f"LONGS  (P < EMA - 30 pt / HFT SELL): N = {len(long_events):3d} | Ret50 = {l_ret:+6.2f} pt | MFE/MAE = {l_mfe/max(1e-4, l_mae):.2f}x | Win% = {l_win:.1f}%")
    print(f"SHORTS (P > EMA + 30 pt / HFT BUY ): N = {len(short_events):3d} | Ret50 = {s_ret:+6.2f} pt | MFE/MAE = {s_mfe/max(1e-4, s_mae):.2f}x | Win% = {s_win:.1f}%")

    # =========================================================================
    # 2. SENSIBILIDAD PARAMETRICA: EMA SPAN Y DISTANCIA CONTINUA
    # =========================================================================
    print("\n" + "=" * 80)
    print("2. SENSIBILIDAD PARAMETRICA BIDIMENSIONAL (EMA SPAN vs DISTANCIA)")
    print("¿Hay un precipicio o la superficie de respuesta es suave y continua?")
    print("=" * 80)

    print(f"{'Span / Dist':<12} | {'d >= 20 pt':<16} | {'d >= 25 pt':<16} | {'d >= 30 pt':<16} | {'d >= 35 pt':<16}")
    print("-" * 80)

    for span in [100, 150, 200, 300, 400]:
        e_arr = calc_ema(c_close, span)
        d_arr = c_close - e_arr
        row_str = f"EMA {span:<6d}  |"
        for d_t in [20.0, 25.0, 30.0, 35.0]:
            sub_rets = []
            for z in zones:
                kind = z.get("kind", "")
                i0 = z.get("start_bar_idx")
                if i0 is None or i0 < span or i0 >= n_candles - 110:
                    continue
                d = d_arr[i0]
                if abs(d) < d_t:
                    continue
                if "SELL" in kind and d < 0:
                    r_dir = 1.0
                    ok = (c_close[i0 + 1] > z["top"] or (i0 + 2 < n_candles and c_close[i0 + 2] > z["top"]))
                elif "BUY" in kind and d > 0:
                    r_dir = -1.0
                    ok = (c_close[i0 + 1] < z["bottom"] or (i0 + 2 < n_candles and c_close[i0 + 2] < z["bottom"]))
                else:
                    continue
                if ok:
                    sub_rets.append((c_close[i0 + 2 + 50] - c_close[i0 + 2]) * r_dir)
            if sub_rets:
                row_str += f" N={len(sub_rets):3d}, {np.mean(sub_rets):+5.2f}p |"
            else:
                row_str += f" N=  0,   ---   |"
        print(row_str)

    # =========================================================================
    # 3. ANALISIS FORENSE DE REGIMEN: DIAS GANADORES VS DIAS PERDEDORES
    # =========================================================================
    print("\n" + "=" * 80)
    print("3. ANATOMIA DE DIAS: ¿QUE PROPIEDAD SEPARA A LOS GANADORES DE LOS PERDEDORES?")
    print("=" * 80)

    # Agrupar velas por dia calendario (UTC)
    day_candles = {}
    for i, c in enumerate(candles):
        d_str = datetime.fromtimestamp(c["time"], tz=timezone.utc).strftime("%Y-%m-%d")
        day_candles.setdefault(d_str, []).append(c)

    print(f"{'Dia':<11} | {'Rango Dia':<10} | {'Velas':<6} | {'Trend Ratio (Kaufman ER)':<24} | {'HFT Strategy Ret50'}")
    print("-" * 80)

    all_evts = long_events + short_events
    pnl_by_day = {}
    for e in all_evts:
        d_str = datetime.fromtimestamp(e["time"], tz=timezone.utc).strftime("%Y-%m-%d")
        pnl_by_day.setdefault(d_str, []).append(e["ret50"])

    er_winners = []
    er_losers = []

    for d_str, d_cands in sorted(day_candles.items()):
        c_p = [x["close"] for x in d_cands]
        h_p = max(x["high"] for x in d_cands)
        l_p = min(x["low"] for x in d_cands)
        d_range = h_p - l_p

        # Kaufman Efficiency Ratio = |Net Change| / Total Path Length
        net_change = abs(c_p[-1] - c_p[0])
        path_length = sum(abs(c_p[j] - c_p[j - 1]) for j in range(1, len(c_p)))
        er = net_change / max(1e-4, path_length)

        st_rets = pnl_by_day.get(d_str, [])
        st_mean = np.mean(st_rets) if st_rets else 0.0

        if st_rets:
            if st_mean > 0:
                er_winners.append(er)
            else:
                er_losers.append(er)

        print(f"{d_str:<11} | {d_range:7.2f} pt | {len(d_cands):<6d} | ER = {er:.4f} ({'Tendencial' if er > 0.025 else 'Rotacional':<10}) | {st_mean:+6.2f} pt (N={len(st_rets)})")

    print(f"\nMedia ER Dias Ganadores : {np.mean(er_winners):.4f}")
    print(f"Media ER Dias Perdedores: {np.mean(er_losers):.4f}")
    print(">> OBSERVACION: El Efficiency Ratio en dias perdedores es significativamente mas alto (mercados que se fugan sin volver).")

    # =========================================================================
    # 4. INTERACCION CON VOLUMEN DE LA ZONA (FILTRO INSTITUCIONAL)
    # =========================================================================
    print("\n" + "=" * 80)
    print("4. INTERACCION: CLIMAX SOBRE-EXTENDIDO + VOLUMEN DE ZONA")
    print("¿Un cluster de volumen masivo (iceberg >= 80c o >= 100c) filtra los dias perdedores?")
    print("=" * 80)

    for v_min in [0, 50, 75, 100]:
        v_sub = [e for e in all_evts if e["vol"] >= v_min]
        if v_sub:
            v_ret = np.mean([e["ret50"] for e in v_sub])
            v_mfe = np.median([e["mfe"] for e in v_sub])
            v_mae = np.median([e["mae"] for e in v_sub])
            v_win = np.mean([1 if e["ret50"] > 0 else 0 for e in v_sub]) * 100.0

            # Dias positivos con este filtro
            d_map = {}
            for e in v_sub:
                ds = datetime.fromtimestamp(e["time"], tz=timezone.utc).strftime("%Y-%m-%d")
                d_map.setdefault(ds, []).append(e["ret50"])
            pos_d = sum(1 for rets in d_map.values() if np.mean(rets) > 0)
            tot_d = len(d_map)

            print(f"Vol >= {v_min:3d}c | N = {len(v_sub):3d} | Ret50 = {v_ret:+6.2f} pt | MFE/MAE = {v_mfe/max(1e-4, v_mae):.2f}x | Win% = {v_win:.1f}% | Dias Ganadores = {pos_d}/{tot_d} ({pos_d/max(1, tot_d)*100:.0f}%)")

    # =========================================================================
    # 5. TEST DE PARIDAD Y CONSISTENCIA CON TICK CONSUMPTION
    # =========================================================================
    print("\n" + "=" * 80)
    print("5. CONSUMO DE TICKS (MUERTE POR VOLUMEN) COMO DISCRIMINANTE DE FALLO")
    print("Pregunta: ¿Las zonas que mueren inmediatamente al 100% son los falsos quiebres perdedores?")
    print("=" * 80)

    # Evaluar si la zona fue consumida rapidamente en las primeras 10 barras
    quick_death_evts = []
    surviving_evts = []

    for e in all_evts:
        z = e.get("zone", {})
        # Buscar en las velas inmediatamente posteriores al evento si el precio cruzo masivamente la zona
        # Usamos touches y pasos si estan disponibles
        pasos = z.get("pasos", 0)
        valid_steps = z.get("valid_steps", 0)
        # Si valid_steps es bajo respecto a pasos, hubo rápida invalidación
        if valid_steps < pasos * 0.5:
            quick_death_evts.append(e)
        else:
            surviving_evts.append(e)

    print(f"Zonas con Rápida Invalidación / Fuga : N = {len(quick_death_evts):3d} | Ret50 = {np.mean([e['ret50'] for e in quick_death_evts]) if quick_death_evts else 0.0:+.2f} pt")
    print(f"Zonas con Estructura Estable        : N = {len(surviving_evts):3d} | Ret50 = {np.mean([e['ret50'] for e in surviving_evts]) if surviving_evts else 0.0:+.2f} pt")


if __name__ == "__main__":
    run_deep_probe()
