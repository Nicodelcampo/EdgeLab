"""Barrido de Tickframes para BigTrap2 (10t, 25t, 50t, 100t, 200t) sobre Oro (GC).

Utiliza la infraestructura canónica de EdgeLab:
1. Reconstrucción de barras de tick y footprints con bars.py.
2. Kernel canónico BigTrap2 v2.2 (edgelab/bridge/indicators/bigtrap2.py).
3. Motor de ejecución estricto First-Touch (edgelab/engine.py).
4. Contraste Monte Carlo de 200 permutaciones contra el modelo nulo.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.bars import build_tick_bars, build_footprints
from edgelab.bridge.indicators.bigtrap2 import run as run_bt2, DEFAULTS
from edgelab.engine import _run, FEES_RT

def load_canonical_ticks(filepath: Path, tick_size: float = 0.10, max_ticks: int = None,
                         allow_truncation: bool = False):
    """Carga una cinta .Last.txt completa.

    `max_ticks=None` (default) NO trunca. Si se pasa un tope y la cinta lo excede,
    la funcion FALLA CERRADO salvo `allow_truncation=True` explicito.

    Historia: hasta 2026-08-23 el default era `max_ticks=700000` y truncaba en
    silencio. La cinta con la que se firmo Puerta 0 (`GC 12-26.Last.txt`) tiene
    683.188 ticks: quedo 16.812 por debajo del tope, un margen del 2,4 %. Una
    cinta mas larga habria producido una comparacion sobre datos truncados con
    veredicto `EXACT` y sin aviso. Ver
    `docs/research/PARIDAD_JUNIO_GC0826_2026-08-23.md` §2.

    Las lineas malformadas tambien se descartaban en silencio; ahora se cuentan
    y se reportan.
    """
    print(f"[*] Cargando ticks desde {filepath.name}...")
    t0 = time.time()
    malformed = 0
    times_ms = []
    prices = []
    bids = []
    asks = []
    volumes = []
    ts_ns = []
    
    count = 0
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split(";")
            if len(parts) < 5:
                malformed += 1
                continue
            try:
                dt_str = parts[0]
                y = int(dt_str[0:4])
                m = int(dt_str[4:6])
                d = int(dt_str[6:8])
                hh = int(dt_str[9:11])
                mm = int(dt_str[11:13])
                ss = int(dt_str[13:15])
                us = int(dt_str[16:22])
                
                from datetime import datetime, timezone
                dt = datetime(y, m, d, hh, mm, ss, us, tzinfo=timezone.utc)
                sec = int(dt.timestamp())
                ms = sec * 1000 + us // 1000
                t_ns = sec * 1_000_000_000 + us * 1_000
                
                p = float(parts[1])
                b = float(parts[2])
                a = float(parts[3])
                v = float(parts[4])
                
                times_ms.append(ms)
                ts_ns.append(t_ns)
                prices.append(p)
                bids.append(b if b > 0 else p - tick_size)
                asks.append(a if a > 0 else p + tick_size)
                volumes.append(v)
                count += 1
                if max_ticks and count >= max_ticks:
                    # FAIL-CLOSED: no truncar en silencio. Si quedan lineas, es truncamiento.
                    resto = sum(1 for _ in f)
                    if resto > 0 and not allow_truncation:
                        raise ValueError(
                            f"load_canonical_ticks: TRUNCAMIENTO en {filepath.name}. "
                            f"max_ticks={max_ticks} alcanzado con {resto} lineas sin leer. "
                            f"Pasa max_ticks=None para cargar la cinta completa, o "
                            f"allow_truncation=True si el recorte es deliberado.")
                    break
            except ValueError:
                raise
            except Exception:
                malformed += 1
                continue

    px_arr = np.array(prices, dtype=np.float64)
    bid_arr = np.array(bids, dtype=np.float64)
    ask_arr = np.array(asks, dtype=np.float64)
    vol_arr = np.array(volumes, dtype=np.float64)
    ms_arr = np.array(times_ms, dtype=np.int64)
    ns_arr = np.array(ts_ns, dtype=np.int64)
    
    px_ticks = np.round(px_arr / tick_size).astype(np.int64)
    bid_ticks = np.round(bid_arr / tick_size).astype(np.int64)
    ask_ticks = np.round(ask_arr / tick_size).astype(np.int64)
    seq_arr = np.arange(len(px_ticks), dtype=np.int64)
    
    ticks = TickSeries(
        ts_ns=ns_arr,
        price_ticks=px_ticks,
        bid_ticks=bid_ticks,
        ask_ticks=ask_ticks,
        volume=vol_arr,
        sequence=seq_arr,
        tick_size=tick_size
    )
    
    print(f"    -> {len(prices):,} ticks listos en {time.time() - t0:.2f}s"
          + (f"  [malformadas descartadas: {malformed:,}]" if malformed else ""))
    return ticks, ms_arr, px_arr, bid_arr, ask_arr, vol_arr

def run_bigtrap2_tickframe_sweep(filepath: Path, tick_size: float = 0.10, tick_value: float = 10.0):
    ticks, times_ms, prices, bids, asks, volumes = load_canonical_ticks(filepath, tick_size)
    
    tickframes = [10, 25, 50, 100, 200]
    
    brackets = [
        {"tp_t": 10, "sl_t": 10, "label": "SL10/TP10 (1:1)"},
        {"tp_t": 20, "sl_t": 10, "label": "SL10/TP20 (2:1)"},
        {"tp_t": 30, "sl_t": 13, "label": "SL13/TP30 (Holdout)"},
        {"tp_t": 15, "sl_t": 8,  "label": "SL8/TP15 (Scalp)"}
    ]
    
    print("\n==========================================================================================")
    print(f"[*] INICIANDO BARRIDO DE TICKFRAMES PARA BigTrap2 EN ORO (GC)")
    print(f"    Tickframes a evaluar: {tickframes}")
    print(f"    Motor: edgelab/engine.py (First-Touch Causal + Spread + 0.5 Ticks Fees)")
    print("==========================================================================================")
    
    all_results = []
    
    for tf in tickframes:
        t0 = time.time()
        print(f"\n------------------------------------------------------------------------------------------")
        print(f"[+] CONSTRUYENDO BARRAS DE {tf} TICKS Y FOOTPRINTS...")
        
        bars = build_tick_bars(ticks, ticks_per_bar=tf)
        footprints = build_footprints(ticks, bars)
        print(f"    -> {len(bars):,} barras construidas en {time.time() - t0:.2f}s")
        
        # Ejecutar kernel BigTrap2 con parámetros estándar
        t_bt2_0 = time.time()
        res = run_bt2(ticks, bars, footprints, params=DEFAULTS)
        zones = res.get("zones", [])
        print(f"    -> {len(zones):,} zonas BigTrap2 detectadas en {time.time() - t_bt2_0:.2f}s")
        
        if len(zones) < 10:
            print("    [!] Muestra insuficiente.")
            continue

        # Mapear cada zona al índice de tick de cierre de su barra de creación
        sig_indices = []
        sig_directions = []
        sig_hours = []
        
        for z in zones:
            bar_idx = z.get("created_bar")
            if bar_idx is None or bar_idx >= len(bars): continue
            
            # Cierre de barra = último tick de la barra
            tick_end_idx = min(len(prices) - 1, (bar_idx + 1) * tf - 1)
            is_bull = z.get("is_bull", True)
            
            # is_bull == True: Compradores atrapados arriba -> Señal SHORT (-1)
            # is_bull == False: Vendedores atrapados abajo -> Señal LONG (+1)
            direction = -1 if is_bull else 1
            
            sig_indices.append(tick_end_idx)
            sig_directions.append(direction)
            
            hour_utc = int((times_ms[tick_end_idx] // 3600000) % 24)
            sig_hours.append(hour_utc)

        sig_i_all = np.array(sig_indices, dtype=np.int64)
        sig_d_all = np.array(sig_directions, dtype=np.int8)
        sig_h_all = np.array(sig_hours, dtype=np.int32)
        
        modes = [
            {"name": "Desnudo (All Day)", "mask": np.ones(len(sig_i_all), dtype=bool)},
            {"name": "Filtro RTH Open (13:30-16 UTC)", "mask": (sig_h_all >= 13) & (sig_h_all < 16)}
        ]
        
        for m in modes:
            sub_i = sig_i_all[m["mask"]]
            sub_d = sig_d_all[m["mask"]]
            n_trades = len(sub_i)
            if n_trades < 10: continue
            
            for b in brackets:
                _, _, _, _, pnl, reason, _, _ = _run(
                    sub_i, sub_d, times_ms, prices, bids, asks,
                    tp_t=b["tp_t"], sl_t=b["sl_t"], max_hold_ms=600_000, tick=tick_size, fees=FEES_RT
                )
                
                valid_pnl = pnl[~np.isnan(pnl)]
                if len(valid_pnl) == 0: continue
                
                net_mean = float(np.mean(valid_pnl))
                net_tot = float(np.sum(valid_pnl))
                win_rate = float(np.sum(valid_pnl > 0) / len(valid_pnl)) * 100.0
                tp_hits = int(np.sum(reason == 0))
                sl_hits = int(np.sum(reason == 1))
                
                # Test Monte Carlo (100 permutaciones)
                rng = np.random.RandomState(42)
                null_means = []
                valid_start, valid_end = 500, len(prices) - 1000
                for _ in range(100):
                    rand_i = rng.randint(valid_start, valid_end, size=n_trades).astype(np.int64)
                    rand_d = rng.choice([-1, 1], size=n_trades).astype(np.int8)
                    _, _, _, _, null_pnl, _, _, _ = _run(
                        rand_i, rand_d, times_ms, prices, bids, asks,
                        tp_t=b["tp_t"], sl_t=b["sl_t"], max_hold_ms=600_000, tick=tick_size, fees=FEES_RT
                    )
                    v_p = null_pnl[~np.isnan(null_pnl)]
                    if len(v_p) > 0: null_means.append(np.mean(v_p))
                    
                p_val = float(np.sum(np.array(null_means) >= net_mean) / len(null_means)) if len(null_means) > 0 else 1.0
                verdict = "EDGE CANDIDATO" if (net_mean > 0.5 and p_val < 0.05) else ("POSITIVO (Marginal)" if net_mean > 0 else "FAIL")
                
                res_row = {
                    "Tickframe": f"{tf} ticks",
                    "Modo": m["name"],
                    "Bracket": b["label"],
                    "N": n_trades,
                    "TP": tp_hits,
                    "SL": sl_hits,
                    "WinRate": f"{win_rate:.1f}%",
                    "Net Ticks/tr": round(net_mean, 3),
                    "Net USD/tr": round(net_mean * tick_value, 2),
                    "Net Total (t)": round(net_tot, 1),
                    "p-val MC": round(p_val, 4),
                    "Veredicto": verdict
                }
                all_results.append(res_row)

    df_res = pd.DataFrame(all_results)
    print("\n==========================================================================================================")
    print("[+] TABLA RESUMEN COMPLETA: BARRIDO DE TICKFRAMES BigTrap2 EN ORO (GC):")
    print("==========================================================================================================")
    df_sorted = df_res.sort_values(by=["Net Ticks/tr", "p-val MC"], ascending=[False, True])
    print(df_sorted.to_string(index=False))
    
    out_csv = REPO_ROOT / "reports_bigtrap2_tickframe_sweep_GC.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\n[+] Reporte exportado a: {out_csv}")

if __name__ == "__main__":
    gc_file = Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8\GC 12-26.Last.txt")
    if gc_file.exists():
        run_bigtrap2_tickframe_sweep(gc_file, tick_size=0.10, tick_value=10.0)
