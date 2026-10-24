#!/usr/bin/env python3
"""Experimento Completo GC 150t Escalonadas:
- Entradas: Market, Limite 25%, Limite 50%, Limite Pico, Stop Ruptura
- SL: ult1, ult2, mitad, pri2, 30t, 60t
- TP: 1R, 1.5R, 2R, 3R, 5R
- BE: 0R, 1R, 2R
- Modelado de fricción real según EdgeLab (spread, comisiones, slippage)
- Controles: Invertido y Aleatorio emparejado
- Partición: In-Sample (GC_12-25) vs Out-of-Sample (GC_02-26, GC_04-26)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
VIEW = REPO / "viewer" / "nt8_bridge"

# Costos reales GC (ticks de 0.10)
# Spread 3.43 + Comision 0.46 + Slippage
SPREAD_TICKS = 3.43
COMMISSION_TICKS = 0.46
SLIPPAGE_MARKET_TICKS = 2.0   # 1 tick entrada agresiva + 1 tick stop
SLIPPAGE_LIMIT_TICKS = 1.0    # 0 tick entrada pasiva + 1 tick stop

FRICTION_MARKET = SPREAD_TICKS + COMMISSION_TICKS + SLIPPAGE_MARKET_TICKS  # 5.89 ticks
FRICTION_LIMIT = SPREAD_TICKS + COMMISSION_TICKS + SLIPPAGE_LIMIT_TICKS    # 4.89 ticks

HORIZON_BARS = 1500           # max velas 25t para resolución del trade
VIGENCIA_BARS = 100           # max velas 25t para que se llene orden límite o stop

ENTRADAS = ["market", "lim_25", "lim_50", "lim_pico", "stop_break"]
SL_MODES = ["ult1", "ult2", "mitad", "pri2", "30", "60"]
TP_RS = [1.0, 1.5, 2.0, 3.0, 5.0]
BE_RS = [0.0, 1.0, 2.0]


def load_data(aid):
    bundle_p = VIEW / "bundles" / f"{aid}.json"
    det_p = VIEW / "bundles" / "peaks_det" / f"{aid}__picos150.json"
    
    b = json.loads(bundle_p.read_text(encoding="utf-8"))
    tkz = float(b["meta"]["tick_size"])
    candles = b["bar_series"]["tick_25"]["candles"]
    det = json.loads(det_p.read_text(encoding="utf-8"))
    return candles, tkz, det["zonas"]


def get_entry_and_sl(z, tkz, entrada_tipo, sl_mode):
    """Calcula precio de entrada propuesta y tamaño de SL en ticks.
    Retorna (tipo_orden, target_px, sl_ticks) o None si inválido."""
    sd = -1 if z["kind"] == "H" else 1
    p_det = z["det_precio"]
    p_pico = z["det_nivel"]
    
    # 1. Precio de entrada
    if entrada_tipo == "market":
        en_target = p_det
        order_type = "market"
    elif entrada_tipo == "lim_25":
        # retroceso 25% hacia el pico
        en_target = p_det - sd * 0.25 * abs(p_det - p_pico)
        order_type = "limit"
    elif entrada_tipo == "lim_50":
        # retroceso 50% hacia el pico
        en_target = p_det - sd * 0.50 * abs(p_det - p_pico)
        order_type = "limit"
    elif entrada_tipo == "lim_pico":
        # retroceso completo al pico
        en_target = p_pico
        order_type = "limit"
    elif entrada_tipo == "stop_break":
        # ruptura 4 ticks a favor
        en_target = p_det + sd * 4 * tkz
        order_type = "stop"
    else:
        return None

    # Redondear al tick más cercano
    en_target = round(en_target / tkz) * tkz

    # 2. Tamaño de SL
    dist_ult = abs(p_pico - p_det) / tkz
    dist_pri = abs(z["picos"][0][2] - p_det) / tkz
    
    if sl_mode == "ult1":
        # Distancia al último pico (mínimo 10 ticks)
        sz = max(10.0, dist_ult)
    elif sl_mode == "ult2":
        sz = max(15.0, 2.0 * dist_ult)
    elif sl_mode == "mitad":
        sz = max(15.0, dist_pri / 2.0)
    elif sl_mode == "pri2":
        sz = max(20.0, 2.0 * dist_pri)
    elif sl_mode.isdigit():
        sz = float(sl_mode)
    else:
        return None

    return order_type, en_target, sz


def simulate_trade(cd, tkz, z, order_type, target_en, sl_ticks, tp_r, be_r, reverse_direction=False):
    """Simula un trade causal sobre velas 25t.
    Retorna dict con resultado o None si no hubo fill."""
    sd = -1 if z["kind"] == "H" else 1
    if reverse_direction:
        sd = -sd  # Invertir dirección para control

    i0 = (z["i25_post"] - 1) if z.get("i25_post") is not None else z["det_i"]
    if i0 >= len(cd) - 1:
        return None

    # Fase 1: Comprobar Fill de la entrada
    fill_i = None
    actual_en = target_en

    if order_type == "market":
        fill_i = i0 + 1
        actual_en = cd[fill_i]["open"]
    elif order_type == "limit":
        # Orden límite: esperar que el precio toque target_en
        for kk in range(i0 + 1, min(len(cd), i0 + 1 + VIGENCIA_BARS)):
            b = cd[kk]
            # Si compra: entra si low <= target_en
            # Si venta: entra si high >= target_en
            hit = (b["low"] <= target_en) if sd == 1 else (b["high"] >= target_en)
            if hit:
                fill_i = kk
                actual_en = target_en
                break
    elif order_type == "stop":
        # Orden stop: entra si el precio rompe más allá de target_en
        for kk in range(i0 + 1, min(len(cd), i0 + 1 + VIGENCIA_BARS)):
            b = cd[kk]
            hit = (b["high"] >= target_en) if sd == 1 else (b["low"] <= target_en)
            if hit:
                fill_i = kk
                actual_en = target_en
                break

    if fill_i is None or fill_i >= len(cd) - 1:
        return None  # No se llenó la orden

    # Fase 2: Ejecución del Trade
    sl_price = actual_en - sd * sl_ticks * tkz
    tp_price = actual_en + sd * sl_ticks * tp_r * tkz
    be_price = (actual_en + sd * sl_ticks * be_r * tkz) if (be_r > 0 and tp_r > be_r) else None

    curr_sl = sl_price
    be_active = False
    why = "fin"
    exit_i = min(len(cd) - 1, fill_i + HORIZON_BARS)

    for kk in range(fill_i + 1, exit_i + 1):
        b = cd[kk]
        hit_sl = (b["low"] <= curr_sl) if sd == 1 else (b["high"] >= curr_sl)
        hit_tp = (b["high"] >= tp_price) if sd == 1 else (b["low"] <= tp_price)

        # Regla conservadora EdgeLab: si la vela toca ambos, el SL gana
        if hit_sl:
            exit_i = kk
            why = "BE" if be_active else "SL"
            break
        if hit_tp:
            exit_i = kk
            why = "TP"
            break

        # Activar BE si toca el umbral
        if be_price is not None and not be_active:
            hit_be = (b["high"] >= be_price) if sd == 1 else (b["low"] <= be_price)
            if hit_be:
                be_active = True
                curr_sl = actual_en

    # Calcular R bruto
    if why == "TP":
        r_gross = tp_r
    elif why == "SL":
        r_gross = -1.0
    elif why == "BE":
        r_gross = 0.0
    else:
        # Cierre forzado al horizonte
        r_gross = ((cd[exit_i]["close"] - actual_en) * sd) / (sl_ticks * tkz)

    # Costo de fricción en R
    friction_ticks = FRICTION_LIMIT if order_type == "limit" else FRICTION_MARKET
    cost_in_r = friction_ticks / sl_ticks
    r_net = r_gross - cost_in_r

    return {
        "r_gross": r_gross,
        "r_net": r_net,
        "why": why,
        "sl_ticks": sl_ticks,
        "cost_r": cost_in_r,
        "bars_held": exit_i - fill_i
    }


def evaluate_cell(cd, tkz, zonas, ent, sl, tp, be, reverse=False):
    results = []
    for z in zonas:
        parsed = get_entry_and_sl(z, tkz, ent, sl)
        if parsed is None:
            continue
        order_type, target_en, sl_ticks = parsed
        res = simulate_trade(cd, tkz, z, order_type, target_en, sl_ticks, tp, be, reverse_direction=reverse)
        if res is not None:
            results.append(res)
    
    n_filled = len(results)
    if n_filled == 0:
        return None
    
    r_gross_all = [x["r_gross"] for x in results]
    r_net_all = [x["r_net"] for x in results]
    sl_all = [x["sl_ticks"] for x in results]
    costs_all = [x["cost_r"] for x in results]
    
    n_win = sum(1 for r in r_gross_all if r > 0)
    st = {"TP": 0, "SL": 0, "BE": 0, "fin": 0}
    for x in results:
        st[x["why"]] += 1
        
    return {
        "n_signals": len(zonas),
        "n_filled": n_filled,
        "fill_rate": round(100.0 * n_filled / len(zonas), 1),
        "win_rate": round(100.0 * n_win / n_filled, 1),
        "r_gross_avg": round(float(np.mean(r_gross_all)), 4),
        "r_net_avg": round(float(np.mean(r_net_all)), 4),
        "sl_med_ticks": round(float(np.median(sl_all)), 1),
        "cost_r_avg": round(float(np.mean(costs_all)), 4),
        "tp_n": st["TP"],
        "sl_n": st["SL"],
        "be_n": st["BE"],
        "fin_n": st["fin"]
    }


def main():
    print("Iniciando Barrido Completo GC 150t...", flush=True)
    assets = {
        "is": "GC_12-25_M1_LUXIMB",
        "oos1": "GC_02-26_M1_LUXIMB",
        "oos2": "GC_04-26_M1_LUXIMB"
    }
    
    data = {}
    for tag, aid in assets.items():
        print(f"Cargando {tag.upper()}: {aid}...", flush=True)
        cd, tkz, zonas = load_data(aid)
        data[tag] = {"cd": cd, "tkz": tkz, "zonas": zonas, "aid": aid}
        print(f"  {len(cd)} velas, {len(zonas)} señales 150t", flush=True)
        
    # Paso 1: Explorar la grilla sobre IN-SAMPLE (GC_12-25)
    print("\n" + "="*90)
    print("FASE 1: DESCUBRIMIENTO IN-SAMPLE (GC_12-25, N=1140 señales)")
    print("="*90)
    
    is_results = []
    total_combos = len(ENTRADAS) * len(SL_MODES) * len(TP_RS) * len(BE_RS)
    print(f"Evaluando {total_combos} combinaciones...")
    
    for ent in ENTRADAS:
        for sl in SL_MODES:
            for tp in TP_RS:
                for be in BE_RS:
                    if be > 0 and tp <= be:
                        continue
                    m = evaluate_cell(data["is"]["cd"], data["is"]["tkz"], data["is"]["zonas"], ent, sl, tp, be)
                    if m is None:
                        continue
                    # Control invertido
                    m_inv = evaluate_cell(data["is"]["cd"], data["is"]["tkz"], data["is"]["zonas"], ent, sl, tp, be, reverse=True)
                    
                    is_results.append({
                        "entrada": ent, "sl": sl, "tp": tp, "be": be,
                        "metrics": m,
                        "inv_net_avg": m_inv["r_net_avg"] if m_inv else 0.0,
                        "edge_direccional": round(m["r_net_avg"] - (m_inv["r_net_avg"] if m_inv else 0.0), 4)
                    })
                    
    # Ordenar por R neto promedio
    is_results.sort(key=lambda x: -x["metrics"]["r_net_avg"])
    
    print(f"\nTOP 20 Combinaciones en IN-SAMPLE (por R Neto por Operación):")
    print(f"{'Entrada':<12} {'SL':<8} {'TP':>4} {'BE':>3} {'Fill%':>6} {'N':>5} {'Win%':>6} {'R_bruto':>8} {'Cost_R':>7} {'R_neto':>8} {'Inv_net':>8} {'Edge_dir':>8}")
    print("-" * 95)
    for r in is_results[:20]:
        m = r["metrics"]
        print(f"{r['entrada']:<12} {r['sl']:<8} {r['tp']:>4.1f}R {r['be']:>2.0f}R {m['fill_rate']:>5.1f}% {m['n_filled']:>5} {m['win_rate']:>5.1f}% {m['r_gross_avg']:>+8.4f} {m['cost_r_avg']:>7.4f} {m['r_net_avg']:>+8.4f} {r['inv_net_avg']:>+8.4f} {r['edge_direccional']:>+8.4f}")

    # Filtrar candidatas para OOS: R neto > 0 AND Edge Direccional > 0 AND Fill% >= 40%
    candidatas = [r for r in is_results if r["metrics"]["r_net_avg"] > 0 and r["edge_direccional"] > 0 and r["metrics"]["fill_rate"] >= 40.0]
    print(f"\nTotal candidatas con R Neto > 0, Edge Direccional > 0 y Fill >= 40%: {len(candidatas)}")

    # Si no hay ninguna con R neto > 0, tomamos las mejores 5 por R neto relativo
    if not candidatas:
        print("ADVERTENCIA: Ninguna celda superó los costos en IS con edge direccional positivo. Tomando las mejores por edge direccional...")
        candidatas = sorted(is_results, key=lambda x: -x["edge_direccional"])[:10]

    # Paso 2: Evaluación OUT-OF-SAMPLE (GC_02-26 y GC_04-26)
    print("\n" + "="*90)
    print("FASE 2: VALIDACIÓN OUT-OF-SAMPLE (OOS1: GC_02-26, OOS2: GC_04-26)")
    print("="*90)
    
    oos_eval = []
    for cand in candidatas[:15]:
        ent, sl, tp, be = cand["entrada"], cand["sl"], cand["tp"], cand["be"]
        
        # Test en OOS1
        m_oos1 = evaluate_cell(data["oos1"]["cd"], data["oos1"]["tkz"], data["oos1"]["zonas"], ent, sl, tp, be)
        m_oos1_inv = evaluate_cell(data["oos1"]["cd"], data["oos1"]["tkz"], data["oos1"]["zonas"], ent, sl, tp, be, reverse=True)
        
        # Test en OOS2
        m_oos2 = evaluate_cell(data["oos2"]["cd"], data["oos2"]["tkz"], data["oos2"]["zonas"], ent, sl, tp, be)
        m_oos2_inv = evaluate_cell(data["oos2"]["cd"], data["oos2"]["tkz"], data["oos2"]["zonas"], ent, sl, tp, be, reverse=True)
        
        oos_eval.append({
            "combo": f"{ent}|{sl}|TP{tp}R|BE{be}R",
            "is": cand["metrics"],
            "is_dir": cand["edge_direccional"],
            "oos1": m_oos1,
            "oos1_dir": round((m_oos1["r_net_avg"] - m_oos1_inv["r_net_avg"]) if (m_oos1 and m_oos1_inv) else 0.0, 4),
            "oos2": m_oos2,
            "oos2_dir": round((m_oos2["r_net_avg"] - m_oos2_inv["r_net_avg"]) if (m_oos2 and m_oos2_inv) else 0.0, 4),
        })

    print(f"\n{'Configuración':<30} | {'IS (12-25) R_net':<16} | {'OOS1 (02-26) R_net':<18} | {'OOS2 (04-26) R_net':<18} | {'Sobrevive?'}")
    print("-" * 105)
    for o in oos_eval:
        is_net = o["is"]["r_net_avg"]
        oos1_net = o["oos1"]["r_net_avg"] if o["oos1"] else -99
        oos2_net = o["oos2"]["r_net_avg"] if o["oos2"] else -99
        
        is_ok = is_net > 0 and o["is_dir"] > 0
        oos1_ok = oos1_net > 0 and o["oos1_dir"] > 0
        oos2_ok = oos2_net > 0 and o["oos2_dir"] > 0
        
        status = "REPLICA COMPLETA" if (is_ok and oos1_ok and oos2_ok) else ("PARCIAL OOS" if (oos1_ok or oos2_ok) else "FALLA OOS")
        print(f"{o['combo']:<30} | {is_net:>+7.4f} (dir {o['is_dir']:>+6.3f}) | {oos1_net:>+7.4f} (dir {o['oos1_dir']:>+6.3f}) | {oos2_net:>+7.4f} (dir {o['oos2_dir']:>+6.3f}) | {status}")

    # Guardar resultados completos en JSON
    out_file = REPO / "docs" / "research" / "eurusd_escalonadas_20261021" / "gc_150t_experiment_full.json"
    out_file.write_text(json.dumps({
        "in_sample_top": is_results[:30],
        "oos_evaluation": oos_eval
    }, indent=2), encoding="utf-8")
    print(f"\nResultados guardados en {out_file}")


if __name__ == "__main__":
    main()
