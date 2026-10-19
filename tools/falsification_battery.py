#!/usr/bin/env python3
"""
tools/falsification_battery.py

BATERÍA DE FALSIFICACIÓN CIENTÍFICA (STRESS-TESTING RIGUROSO)
Diseñada para intentar derribar y falsar los hallazgos favorables:
  1. Test Placebo / Pseudo-Señal: ¿Aporta algo el HFT o cualquier vela extrema da lo mismo?
  2. Test de Causalidad Estricta (Lookahead Zero): Entrada en la barra exacta sin peeking a 6 barras.
  3. Simulación con Fricciones Reales CME y Stop-Loss Estructural (P&L Real).
  4. De-duplicación de Clusters (Independencia temporal y N efectivo).
  5. Descomposición por Régimen de Sesión: RTH (alta liquidez/tendencia) vs ETH (overnight/rango).
  6. Estabilidad Temporal por Día (Jackknife / Cross-day robustness).
"""

import json
import math
import sys
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


def run_falsification():
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

    ema200 = calc_ema(c_close, 200)
    dist200 = c_close - ema200

    print("=" * 80)
    print("BATERIA DE FALSIFICACION CIENTIFICA — EDGELAB AUDIT")
    print(f"Muestra: NQ 06-26 | Velas 25t: {n_candles:,} | Zonas: {len(zones):,}")
    print("=" * 80)

    # =========================================================================
    # TEST 1: HIPOTESIS PLACEBO (GENERIC EXTREME VS HFT ALPHA)
    # ¿El edge proviene del HFT o de la simple sobre-extension de la EMA?
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: CONTROL PLACEBO (PSEUDO-SENAL SIN HFT)")
    print("Pregunta: Si entramos en CUALQUIER vela sobre-extendida (|d| >= 30 pt) con")
    print("reversion de vela (sin zona HFT), ¿obtenemos el mismo resultado?")
    print("=" * 80)

    # Identificar todas las barras con |d| >= 30 pt y giro de vela
    generic_events = []
    # Usar paso 10 para evitar sobre-muestreo continuo
    for i in range(200, n_candles - 110, 5):
        d = dist200[i]
        if abs(d) < 30.0:
            continue
        # Sobre-extendido a la baja y vela alcista que cierra sobre el high previo
        if d < -30.0 and c_close[i] > c_open[i] and c_close[i] > c_high[i - 1]:
            sig_dir = 1.0
        elif d > 30.0 and c_close[i] < c_open[i] and c_close[i] < c_low[i - 1]:
            sig_dir = -1.0
        else:
            continue

        entry_p = c_close[i]
        sub_high = c_high[i + 1 : i + 52]
        sub_low = c_low[i + 1 : i + 52]
        ret50 = (c_close[i + 50] - entry_p) * sig_dir
        mfe = np.max(sub_high) - entry_p if sig_dir == 1.0 else entry_p - np.min(sub_low)
        mae = entry_p - np.min(sub_low) if sig_dir == 1.0 else np.max(sub_high) - entry_p
        generic_events.append({"ret50": ret50, "mfe": mfe, "mae": mae})

    # Eventos HFT con d >= 30 pt (del script previo)
    hft_events = []
    for z in zones:
        kind = z.get("kind", "")
        i0 = z.get("start_bar_idx")
        if i0 is None or i0 < 200 or i0 >= n_candles - 110:
            continue
        d = dist200[i0]
        if abs(d) < 30.0:
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
        sub_high = c_high[entry_idx + 1 : entry_idx + 52]
        sub_low = c_low[entry_idx + 1 : entry_idx + 52]
        ret50 = (c_close[entry_idx + 50] - entry_p) * rev_dir
        mfe = np.max(sub_high) - entry_p if rev_dir == 1.0 else entry_p - np.min(sub_low)
        mae = entry_p - np.min(sub_low) if rev_dir == 1.0 else np.max(sub_high) - entry_p
        hft_events.append({"ret50": ret50, "mfe": mfe, "mae": mae, "time": c_time[entry_idx], "idx": entry_idx, "dir": rev_dir, "zone": z})

    gen_ret = np.mean([e["ret50"] for e in generic_events])
    gen_mfe = np.median([e["mfe"] for e in generic_events])
    gen_mae = np.median([e["mae"] for e in generic_events])

    hft_ret = np.mean([e["ret50"] for e in hft_events])
    hft_mfe = np.median([e["mfe"] for e in hft_events])
    hft_mae = np.median([e["mae"] for e in hft_events])

    print(f"Generic Placebo (Sin HFT) : N = {len(generic_events):4d} | Ret50 = {gen_ret:+.2f} pt | MFE/MAE = {gen_mfe/gen_mae:.2f}x")
    print(f"HFT Climax + Reversion    : N = {len(hft_events):4d} | Ret50 = {hft_ret:+.2f} pt | MFE/MAE = {hft_mfe/hft_mae:.2f}x")
    diff_alpha = hft_ret - gen_ret
    print(f"Alpha Incremental del HFT : {diff_alpha:+.2f} pt ({diff_alpha*4:+.1f} ticks)")
    if diff_alpha <= 0.2:
        print(">> DICTAMEN: ADVERTENCIA. El HFT no anade alpha significativo sobre el placebo generico.")
    else:
        print(">> DICTAMEN: SUPERADO. El HFT aporta alpha genuino superior al placebo generico.")

    # =========================================================================
    # TEST 2: CAUSALIDAD ESTRICTA Y LOOKAHEAD ZERO EN EL RE-TEST
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: AUDITORIA DE LOOKAHEAD EN RE-TEST (CAUSALIDAD INSTANTANEA)")
    print("Pregunta: Si entramos estrictamente en la barra de contacto sin esperar 6 barras")
    print("de evaluacion a futuro, ¿el edge sobrevive o desaparece?")
    print("=" * 80)

    strict_retests = []
    for z in zones:
        kind = z.get("kind", "")
        i0 = z.get("start_bar_idx")
        if i0 is None or i0 < 200 or i0 >= n_candles - 110:
            continue
        z_bot = min(z["top"], z["bottom"])
        z_top = max(z["top"], z["bottom"])
        rev_dir = 1.0 if "SELL" in kind else -1.0

        # Paso 1: Despegue causal inicial
        bounced = False
        retest_bar = -1
        for ci in range(i0 + 1, min(n_candles - 110, i0 + 100)):
            if not bounced:
                if rev_dir == 1.0 and c_high[ci] >= z_top + 4 * tick_size:
                    bounced = True
                elif rev_dir == -1.0 and c_low[ci] <= z_bot - 4 * tick_size:
                    bounced = True
            else:
                # Paso 2: Re-test instantaneo en tiempo real
                # El precio toca la zona
                if c_low[ci] <= z_top and c_high[ci] >= z_bot:
                    # En tiempo real, evaluamos el cierre de ESTA MISMA BARRA (ci)
                    # Si no quebro el piso/techo en esta barra:
                    if rev_dir == 1.0 and c_close[ci] >= z_bot:
                        retest_bar = ci
                        break
                    elif rev_dir == -1.0 and c_close[ci] <= z_top:
                        retest_bar = ci
                        break
                    else:
                        break  # Perforo de entrada

        if retest_bar != -1:
            # Entrada ESTRICTAMENTE CAUSAL en el open de la siguiente vela (retest_bar + 1)
            entry_p = c_open[retest_bar + 1]
            sub_high = c_high[retest_bar + 1 : retest_bar + 52]
            sub_low = c_low[retest_bar + 1 : retest_bar + 52]
            ret50 = (c_close[retest_bar + 51] - entry_p) * rev_dir
            mfe = np.max(sub_high) - entry_p if rev_dir == 1.0 else entry_p - np.min(sub_low)
            mae = entry_p - np.min(sub_low) if rev_dir == 1.0 else np.max(sub_high) - entry_p
            strict_retests.append({"ret50": ret50, "mfe": mfe, "mae": mae, "vol": z.get("vol", 0)})

    s_ret = np.mean([e["ret50"] for e in strict_retests])
    s_mfe = np.median([e["mfe"] for e in strict_retests])
    s_mae = np.median([e["mae"] for e in strict_retests])
    print(f"Re-test Causal Estricto (Todo Vol) : N={len(strict_retests):4d} | Ret50={s_ret:+.2f} pt | MFE/MAE={s_mfe/s_mae:.2f}x")

    strict_vol90 = [e for e in strict_retests if e["vol"] >= 90]
    if strict_vol90:
        sv_ret = np.mean([e["ret50"] for e in strict_vol90])
        sv_mfe = np.median([e["mfe"] for e in strict_vol90])
        sv_mae = np.median([e["mae"] for e in strict_vol90])
        print(f"Re-test Causal Estricto (Vol >= 90): N={len(strict_vol90):4d} | Ret50={sv_ret:+.2f} pt | MFE/MAE={sv_mfe/sv_mae:.2f}x")

    # =========================================================================
    # TEST 3: FRICCIONES REALES CME Y SIMULACION CON STOP-LOSS ESTRUCTURAL
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: FRICCIONES REALES CME ($4.50 COMISION + 1T SLIPPAGE) Y STOP-LOSS")
    print("Pregunta: ¿Sobrevive la estrategia a un Stop Loss real colocado 3 ticks")
    print("detras de la zona y comisiones completas?")
    print("=" * 80)

    # Fricciones:
    # NQ tick = 0.25 pt = $5.00 USD
    # Comision RT = $4.50 = 0.9 ticks = 0.225 pt
    # Slippage Stop = 1 tick = 0.25 pt
    # Spread/Slippage Entry = 1 tick = 0.25 pt
    # Costo total friccion por trade = 0.725 pt (~3 ticks = $14.50 USD)
    FRICTION_PT = 0.75

    pnl_trades = []
    for e in hft_events:
        z = e["zone"]
        entry_idx = e["idx"]
        entry_p = c_close[entry_idx]
        rev_dir = e["dir"]
        z_bot = min(z["top"], z["bottom"])
        z_top = max(z["top"], z["bottom"])

        # SL estructural: 3 ticks mas alla de la zona
        if rev_dir == 1.0:
            sl_price = z_bot - 3 * tick_size
            tp_price = ema200[entry_idx]  # Target = EMA
        else:
            sl_price = z_top + 3 * tick_size
            tp_price = ema200[entry_idx]

        sl_dist = abs(entry_p - sl_price)
        tp_dist = abs(tp_price - entry_p)

        # Si el target esta mas cerca que el stop o es ilogico, target minimo 10 pt
        if tp_dist < 5.0:
            tp_dist = 10.0
            tp_price = entry_p + 10.0 * rev_dir

        # Simular trayectoria tick a tick (barra por barra)
        outcome_pnl = None
        for step in range(1, 101):
            cur_idx = entry_idx + step
            if cur_idx >= n_candles:
                break
            b_high = c_high[cur_idx]
            b_low = c_low[cur_idx]

            # Verificar Stop
            if rev_dir == 1.0:
                if b_low <= sl_price:
                    outcome_pnl = -sl_dist - FRICTION_PT
                    break
                elif b_high >= tp_price:
                    outcome_pnl = tp_dist - FRICTION_PT
                    break
            else:
                if b_high >= sl_price:
                    outcome_pnl = -sl_dist - FRICTION_PT
                    break
                elif b_low <= tp_price:
                    outcome_pnl = tp_dist - FRICTION_PT
                    break

        if outcome_pnl is None:
            # Cierre por tiempo a 100 barras
            exit_p = c_close[min(n_candles - 1, entry_idx + 100)]
            outcome_pnl = (exit_p - entry_p) * rev_dir - FRICTION_PT

        pnl_trades.append({"pnl": outcome_pnl, "sl_dist": sl_dist, "tp_dist": tp_dist})

    pnl_arr = np.array([t["pnl"] for t in pnl_trades])
    win_trades = pnl_arr > 0
    total_net_pnl = np.sum(pnl_arr)
    gross_win = np.sum(pnl_arr[pnl_arr > 0])
    gross_loss = abs(np.sum(pnl_arr[pnl_arr < 0]))
    pf = gross_win / max(1e-4, gross_loss)
    win_rate = np.mean(win_trades) * 100.0

    print(f"Total Trades Simulados (HFT Climax + Reversion) : {len(pnl_arr)}")
    print(f"Win Rate con SL/TP Real                          : {win_rate:.1f}%")
    print(f"PnL Neto Total (en Puntos NQ)                    : {total_net_pnl:+.2f} pts (${total_net_pnl*20:,.2f} USD)")
    print(f"PnL Medio por Trade (Neto de Fricciones)         : {np.mean(pnl_arr):+.2f} pts (${np.mean(pnl_arr)*20:+.2f} USD)")
    print(f"Profit Factor Real                               : {pf:.2f}")

    if pf < 1.0:
        print(">> DICTAMEN: FALSADO. Con Stop Loss estructural y fricciones reales, el Profit Factor cae bajo 1.0.")
    elif pf < 1.2:
        print(">> DICTAMEN: MARGINAL. El edge sobrevive pero es debil frente a la varianza.")
    else:
        print(">> DICTAMEN: SUPERADO. El edge resiste fricciones reales y Stop Loss con PF > 1.20.")

    # =========================================================================
    # TEST 4: DE-DUPLICACION DE CLUSTERS (INDEPENDENCIA TEMPORAL)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: CLUSTER OVERLAP Y DE-DUPLICACION (MUESTRA EFECTIVA)")
    print("Pregunta: ¿Estamos contando multiples veces la misma ola de reversion?")
    print("Se exige un espaciado minimo de 50 barras (~20 min) entre entradas consecutivas.")
    print("=" * 80)

    dedup_events = []
    last_idx = -999
    for e in hft_events:
        if e["idx"] - last_idx >= 50:
            dedup_events.append(e)
            last_idx = e["idx"]

    dedup_ret = np.mean([e["ret50"] for e in dedup_events])
    dedup_mfe = np.median([e["mfe"] for e in dedup_events])
    dedup_mae = np.median([e["mae"] for e in dedup_events])

    print(f"Eventos Originales : {len(hft_events)}")
    print(f"Eventos De-duplicados (Min 50b) : {len(dedup_events)} (Reduccion: {(1 - len(dedup_events)/len(hft_events))*100:.1f}%)")
    print(f"Retorno Medio H=50 De-duplicado : {dedup_ret:+.2f} pt")
    print(f"MFE/MAE Ratio De-duplicado      : {dedup_mfe/dedup_mae:.2f}x")

    # =========================================================================
    # TEST 5: REGIMEN DE SESION (RTH VS ETH)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 5: SESION RTH (09:30 - 16:00 ET) VS ETH (OVERNIGHT/PRE-MARKET)")
    print("Pregunta: ¿El edge es un artefacto de baja liquidez nocturna y desaparece en RTH?")
    print("=" * 80)

    rth_events = []
    eth_events = []
    for e in hft_events:
        dt = datetime.fromtimestamp(e["time"], tz=timezone.utc)
        # NQ RTH es 13:30 a 20:00 UTC (09:30 - 16:00 ET en horario de verano EDT)
        minute_of_day = dt.hour * 60 + dt.minute
        is_rth = (13 * 60 + 30) <= minute_of_day < (20 * 60)
        if is_rth:
            rth_events.append(e)
        else:
            eth_events.append(e)

    rth_ret = np.mean([e["ret50"] for e in rth_events]) if rth_events else 0.0
    eth_ret = np.mean([e["ret50"] for e in eth_events]) if eth_events else 0.0

    rth_mfe = np.median([e["mfe"] for e in rth_events]) if rth_events else 0.0
    rth_mae = np.median([e["mae"] for e in rth_events]) if rth_events else 0.0
    eth_mfe = np.median([e["mfe"] for e in eth_events]) if eth_events else 0.0
    eth_mae = np.median([e["mae"] for e in eth_events]) if eth_events else 0.0

    print(f"RTH (Sesion Regular US) : N = {len(rth_events):3d} | Ret50 = {rth_ret:+.2f} pt | MFE/MAE = {rth_mfe/max(1e-4, rth_mae):.2f}x")
    print(f"ETH (Overnight/Pre-mkt) : N = {len(eth_events):3d} | Ret50 = {eth_ret:+.2f} pt | MFE/MAE = {eth_mfe/max(1e-4, eth_mae):.2f}x")

    if rth_ret < 0:
        print(">> DICTAMEN: ADVERTENCIA CRITICA. El edge desaparece o es negativo durante RTH.")
    else:
        print(">> DICTAMEN: SUPERADO. El edge se mantiene positivo durante RTH.")

    # =========================================================================
    # TEST 6: ESTABILIDAD TEMPORAL POR DIA (CROSS-DAY JACKKNIFE)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 6: CONSISTENCIA TEMPORAL DIA A DIA (JACKKNIFE)")
    print("Pregunta: ¿El resultado depende de 1 o 2 dias anomalos o es consistente?")
    print("=" * 80)

    by_day = {}
    for e in hft_events:
        day_str = datetime.fromtimestamp(e["time"], tz=timezone.utc).strftime("%Y-%m-%d")
        by_day.setdefault(day_str, []).append(e["ret50"])

    print(f"{'Dia':<12} | {'N':<4} | {'Ret Mean':<10} | {'Ret Median':<10} | {'Win%':<6}")
    print("-" * 52)
    pos_days = 0
    total_days = len(by_day)
    for day, rets in sorted(by_day.items()):
        m_r = np.mean(rets)
        med_r = np.median(rets)
        w_r = np.mean(np.array(rets) > 0) * 100.0
        if m_r > 0:
            pos_days += 1
        print(f"{day:<12} | {len(rets):<4d} | {m_r:+8.2f} pt | {med_r:+8.2f} pt | {w_r:5.1f}%")

    print(f"\nDias Positivos: {pos_days} de {total_days} ({pos_days/total_days*100:.1f}%)")
    if pos_days / total_days < 0.60:
        print(">> DICTAMEN: INESTABLE. Menos del 60% de los dias presentan expectativa positiva.")
    else:
        print(">> DICTAMEN: SUPERADO. Consistencia interdiaria solida (>= 60% de dias verdes).")


if __name__ == "__main__":
    run_falsification()
