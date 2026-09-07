#!/usr/bin/env python3
"""Analiza los eventos de FILL generados por NinjaTrader 8 y mide su trayectoria MFE/MAE."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

LOG_PATH = Path(r"C:\Users\Usuario\Documents\NinjaTrader 8\BigTrap2AbsorptionES_events__ES__TW100.csv")

def main():
    if not LOG_PATH.is_file():
        print(f"Error: {LOG_PATH} no existe.")
        return

    bars = {}
    fills = []
    zones = []

    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split("|")
            if len(parts) < 4:
                continue
            seq, t_str, ev_type, payload = parts[0], parts[1], parts[2], parts[3]
            
            p_dict = dict(item.split("=", 1) for item in payload.split(";") if "=" in item)
            
            if ev_type == "TRAP":
                bar_num = int(p_dict.get("bar", -1))
                if bar_num >= 0 and bar_num not in bars:
                    bars[bar_num] = {
                        "time": t_str,
                        "close": float(p_dict.get("close", 0)),
                        "bar_vol": float(p_dict.get("bar_vol", 0)),
                    }
            elif ev_type == "ZONE_CREATED":
                zones.append(p_dict)
            elif ev_type == "FILL":
                fills.append({
                    "seq": seq,
                    "time": t_str,
                    "side": p_dict.get("side"),
                    "dir": p_dict.get("dir"),
                    "fill_px": float(p_dict.get("fill_px", 0)),
                    "a_score": float(p_dict.get("a_score", 0)),
                    "fill_bar": int(p_dict.get("fill_bar", -1)),
                })

    df_fills = pd.DataFrame(fills)
    print(f"[*] Total FILLs leídos: {len(df_fills)}")
    print(f"[*] Total barras con precio registradas: {len(bars)}")
    
    if df_fills.empty:
        return

    # Mapeo de barras ordenadas
    sorted_bar_nums = sorted(bars.keys())
    bar_to_idx = {b: i for i, b in enumerate(sorted_bar_nums)}
    bar_prices = [bars[b]["close"] for b in sorted_bar_nums]
    
    results = []
    
    for _, row in df_fills.iterrows():
        f_bar = row["fill_bar"]
        f_px = row["fill_px"]
        direction = 1 if row["dir"] == "long" else -1
        
        # Buscar precios posteriores
        # Las barras en el log corresponden a los bloques procesados
        subsequent_bars = [b for b in sorted_bar_nums if b >= f_bar]
        if not subsequent_bars:
            continue
            
        future_pxs = [bars[b]["close"] for b in subsequent_bars[:100]]
        
        # MFE / MAE en las siguientes 10, 30, 50 barras
        deltas = [(px - f_px) * direction for px in future_pxs]
        
        mfe_10 = max(deltas[:10]) if len(deltas) >= 1 else 0
        mae_10 = min(deltas[:10]) if len(deltas) >= 1 else 0
        
        mfe_30 = max(deltas[:30]) if len(deltas) >= 1 else 0
        mae_30 = min(deltas[:30]) if len(deltas) >= 1 else 0
        
        mfe_50 = max(deltas[:50]) if len(deltas) >= 1 else 0
        mae_50 = min(deltas[:50]) if len(deltas) >= 1 else 0
        
        ret_10 = deltas[min(9, len(deltas)-1)] if len(deltas) else 0
        ret_30 = deltas[min(29, len(deltas)-1)] if len(deltas) else 0
        ret_50 = deltas[min(49, len(deltas)-1)] if len(deltas) else 0

        results.append({
            "time": row["time"][11:19],
            "dir": row["dir"].upper(),
            "fill_px": f_px,
            "score": row["a_score"],
            "mfe_10_pts": mfe_10,
            "mae_10_pts": mae_10,
            "mfe_30_pts": mfe_30,
            "mae_30_pts": mae_30,
            "mfe_50_pts": mfe_50,
            "mae_50_pts": mae_50,
            "ret_10_pts": ret_10,
            "ret_30_pts": ret_30,
            "ret_50_pts": ret_50,
        })

    df_res = pd.DataFrame(results)
    
    print("\n" + "=" * 95)
    print("DETALLE INDIVIDUAL DE LOS 24 FILLS DE BIGTRAP2ABSORPTION EN ES:")
    print("=" * 95)
    print(f"{'Hora':<9} | {'Dir':<5} | {'Fill Px':>8} | {'Score':>7} | {'MFE 10b':>8} | {'MAE 10b':>8} | {'MFE 30b':>8} | {'MAE 30b':>8} | {'Ret 30b':>8}")
    print("-" * 95)
    for _, r in df_res.iterrows():
        print(f"{r['time']:<9} | {r['dir']:<5} | {r['fill_px']:>8.2f} | {r['score']:>7.1f} | {r['mfe_10_pts']:>7.2f}p | {r['mae_10_pts']:>7.2f}p | {r['mfe_30_pts']:>7.2f}p | {r['mae_30_pts']:>7.2f}p | {r['ret_30_pts']:>7.2f}p")
    
    print("-" * 95)
    print("\nRESUMEN ESTADÍSTICO AGREGADO (ES 09-26):")
    print(f"Total Fills: {len(df_res)} ({sum(df_res['dir']=='LONG')} LONG, {sum(df_res['dir']=='SHORT')} SHORT)")
    print(f"MFE Promedio @ 10 barras (1.000 ticks): {df_res['mfe_10_pts'].mean():+.2f} pts (${df_res['mfe_10_pts'].mean()*50:+.2f})")
    print(f"MAE Promedio @ 10 barras (1.000 ticks): {df_res['mae_10_pts'].mean():+.2f} pts (${df_res['mae_10_pts'].mean()*50:+.2f})")
    print(f"MFE Promedio @ 30 barras (3.000 ticks): {df_res['mfe_30_pts'].mean():+.2f} pts (${df_res['mfe_30_pts'].mean()*50:+.2f})")
    print(f"MAE Promedio @ 30 barras (3.000 ticks): {df_res['mae_30_pts'].mean():+.2f} pts (${df_res['mae_30_pts'].mean()*50:+.2f})")
    print(f"MFE Promedio @ 50 barras (5.000 ticks): {df_res['mfe_50_pts'].mean():+.2f} pts (${df_res['mfe_50_pts'].mean()*50:+.2f})")
    print(f"MAE Promedio @ 50 barras (5.000 ticks): {df_res['mae_50_pts'].mean():+.2f} pts (${df_res['mae_50_pts'].mean()*50:+.2f})")
    print(f"Retorno Promedio @ 10 barras: {df_res['ret_10_pts'].mean():+.2f} pts")
    print(f"Retorno Promedio @ 30 barras: {df_res['ret_30_pts'].mean():+.2f} pts")
    print(f"Retorno Promedio @ 50 barras: {df_res['ret_50_pts'].mean():+.2f} pts")
    print(f"Ratio MFE/MAE @ 30 barras: {abs(df_res['mfe_30_pts'].mean() / df_res['mae_30_pts'].mean()):.2f}x")

if __name__ == '__main__':
    main()
