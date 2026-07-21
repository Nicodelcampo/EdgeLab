import numpy as np
import pandas as pd
from numba import njit, prange
import pyarrow.parquet as pq
from pathlib import Path
import time

from edgelab.config import EURUSD_TICKS

@njit(cache=True)
def extract_magnet_events(times_ms, last, tick_size=1.0):
    n = len(last)
    
    max_events = 500_000
    ev_time = np.zeros(max_events, dtype=np.int64)
    ev_type = np.zeros(max_events, dtype=np.int8) # 1 = Long targeting PDH, -1 = Short targeting PDL
    ev_dist = np.zeros(max_events, dtype=np.float64) # Distance to target (TP)
    ev_mom = np.zeros(max_events, dtype=np.float64)  # Momentum in last 15m
    ev_mfe = np.zeros(max_events, dtype=np.float64)
    ev_mae = np.zeros(max_events, dtype=np.float64)
    
    m = 0
    current_day = -1
    high_today = -1.0
    low_today = 1e9
    
    pdh = -1.0
    pdl = -1.0
    
    last_scan_time = 0
    SCAN_INTERVAL = 300_000 # 5 minutes
    
    for i in range(1, n):
        t = times_ms[i]
        day = t // 86400000
        
        if day != current_day:
            if current_day != -1:
                pdh = high_today
                pdl = low_today
            current_day = day
            high_today = last[i]
            low_today = last[i]
            
        if last[i] > high_today: high_today = last[i]
        if last[i] < low_today: low_today = last[i]
        
        if pdh == -1.0: continue
        
        if t - last_scan_time >= SCAN_INTERVAL:
            last_scan_time = t
            h = (t // 3600000) % 24
            
            # Solo buscar setups durante la ventana liquida (London + NY)
            if h < 7 or h >= 17:
                continue
                
            # Calcular momentum previo (15 mins)
            idx_15m = i
            while idx_15m > 0 and t - times_ms[idx_15m] < 900_000:
                idx_15m -= 1
                
            # Distancia al PDH (Target para Longs)
            dist_pdh = (pdh - last[i]) / tick_size
            if dist_pdh > 0: # El precio esta por debajo del PDH
                mom_15m = (last[i] - last[idx_15m]) / tick_size # Positivo = subiendo hacia PDH
                
                # Calcular MFE y MAE (Look forward 120 mins o hasta fin de dia)
                idx_fwd = i
                max_px = last[i]
                min_px = last[i]
                while idx_fwd < n and times_ms[idx_fwd] - t < 7200_000: # 120 mins
                    if last[idx_fwd] > max_px: max_px = last[idx_fwd]
                    if last[idx_fwd] < min_px: min_px = last[idx_fwd]
                    # Cortar si ya toco el target exacto (no necesitamos ver mas alla si cobramos TP)
                    if last[idx_fwd] >= pdh:
                        max_px = pdh
                        break
                    idx_fwd += 1
                    
                ev_time[m] = t
                ev_type[m] = 1
                ev_dist[m] = dist_pdh
                ev_mom[m] = mom_15m
                ev_mfe[m] = (max_px - last[i]) / tick_size
                ev_mae[m] = (last[i] - min_px) / tick_size
                m += 1
                
            if m >= max_events: break
                
            # Distancia al PDL (Target para Shorts)
            dist_pdl = (last[i] - pdl) / tick_size
            if dist_pdl > 0: # El precio esta por encima del PDL
                mom_15m = (last[idx_15m] - last[i]) / tick_size # Positivo = bajando hacia PDL
                
                # Calcular MFE y MAE
                idx_fwd = i
                max_px = last[i]
                min_px = last[i]
                while idx_fwd < n and times_ms[idx_fwd] - t < 7200_000: # 120 mins
                    if last[idx_fwd] > max_px: max_px = last[idx_fwd]
                    if last[idx_fwd] < min_px: min_px = last[idx_fwd]
                    # Cortar si ya toco el target
                    if last[idx_fwd] <= pdl:
                        min_px = pdl
                        break
                    idx_fwd += 1
                    
                ev_time[m] = t
                ev_type[m] = -1
                ev_dist[m] = dist_pdl
                ev_mom[m] = mom_15m
                ev_mfe[m] = (last[i] - min_px) / tick_size
                ev_mae[m] = (max_px - last[i]) / tick_size
                m += 1
                
            if m >= max_events: break
            
    return ev_time[:m], ev_type[:m], ev_dist[:m], ev_mom[:m], ev_mfe[:m], ev_mae[:m]

def run_miner():
    print(f"Cargando {EURUSD_TICKS}...")
    tbl = pq.read_table(EURUSD_TICKS)
    times_ms = tbl.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[ms]").astype(np.int64)
    last = np.round(tbl.column("last").to_numpy(zero_copy_only=False).astype(np.float64) * 100000.0, 1)
    
    print("Escaneando el mercado (cada 5 min) hacia Imanes PDH/PDL...")
    t0 = time.time()
    t_ev, typ_ev, dist_ev, mom_ev, mfe_ev, mae_ev = extract_magnet_events(times_ms, last, tick_size=1.0)
    print(f"Extraccion completada en {time.time()-t0:.2f} segs. {len(t_ev):,} eventos.")
    
    df = pd.DataFrame({
        "time_ms": t_ev,
        "type": typ_ev,
        "dist": dist_ev,
        "mom": mom_ev,
        "mfe": mfe_ev,
        "mae": mae_ev
    })
    
    split_idx = int(len(df) * 0.7)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    print(f"In-Sample: {len(train):,} eventos | Out-Of-Sample: {len(test):,}")
    
    # Parametros para forzar (Grid Search)
    min_dists = [100, 200, 300]     # Distancia min al target: 10, 20, 30 pips
    max_dists = [300, 500, 800]     # Distancia max al target: 30, 50, 80 pips
    min_moms = [0, 50, 100, 200]    # Momentum previo min: 0, 5, 10, 20 pips a favor
    sl_factors = [0.5, 1.0, 2.0]    # SL como fraccion del TP (ej. 0.5 = R:R 1:2)
    
    results = []
    print("Corriendo Fuerza Bruta (Targets)...")
    for d_min in min_dists:
        for d_max in max_dists:
            if d_min >= d_max: continue
            for mom in min_moms:
                for sl_f in sl_factors:
                    # Filtrar escenarios
                    mask = (train["dist"] >= d_min) & (train["dist"] <= d_max) & (train["mom"] >= mom)
                    sub = train[mask]
                    if len(sub) < 50: continue
                    
                    # Target dinamico es exactamente la distancia ("dist")
                    # Stop loss dinamico es SL_factor * dist
                    sl_array = sub["dist"] * sl_f
                    
                    # Trade wins if MFE reaches Target BEFORE MAE reaches SL
                    # As approximation: if MFE >= dist and MAE < sl_array -> WIN
                    # In real path, if both are hit, we don't know which hit first without full tick replay,
                    # but since our Numba kernel breaks the MFE/MAE loop exactly when Target is hit,
                    # if MAE < sl_array at the time the Target was hit, it's a guaranteed win.
                    
                    wins = (sub["mfe"] >= sub["dist"]) & (sub["mae"] < sl_array)
                    wr = wins.mean()
                    n = len(sub)
                    
                    # Expectancy en "pipettes" normalizado (usamos el mean TP y mean SL de los trades validos)
                    mean_tp = sub["dist"].mean()
                    mean_sl = sl_array.mean()
                    exp_net = wr * mean_tp - (1-wr) * mean_sl - 6.0 # 6 ticks spread+com
                    
                    results.append({
                        "d_min": d_min, "d_max": d_max, "min_mom": mom, "sl_fact": sl_f,
                        "n": n, "wr": wr, "exp": exp_net, "mean_tp": mean_tp
                    })
                        
    res = pd.DataFrame(results).sort_values("exp", ascending=False)
    print("\nTOP 5 RESULTADOS IN-SAMPLE:")
    print(res.head(5).to_string(index=False))
    
    if len(res) == 0 or res.iloc[0]["exp"] <= 0:
        print("\nNINGUN EDGE ENCONTRADO IN-SAMPLE (>0 despues de costos).")
        return
        
    print("\nValidando OOS...")
    best = res.iloc[0]
    mask_test = (test["dist"] >= best["d_min"]) & (test["dist"] <= best["d_max"]) & (test["mom"] >= best["min_mom"])
    sub_test = test[mask_test]
    
    if len(sub_test) < 10:
        print("Muy pocos trades en OOS para validar.")
        return
        
    sl_array_test = sub_test["dist"] * best["sl_fact"]
    wins_test = (sub_test["mfe"] >= sub_test["dist"]) & (sub_test["mae"] < sl_array_test)
    wr_test = wins_test.mean()
    mean_tp_test = sub_test["dist"].mean()
    mean_sl_test = sl_array_test.mean()
    exp_test = wr_test * mean_tp_test - (1-wr_test) * mean_sl_test - 6.0
    
    print(f"OOS Expectancy: {exp_test:.2f} ticks (WR {wr_test:.1%}, n={len(sub_test)})")
    if exp_test > 0:
        print("VEREDICTO: EDGE ENCONTRADO EN OOS! Funciona como Imán.")
    else:
        print("VEREDICTO: Falso Edge. Destruido en OOS.")

if __name__ == "__main__":
    run_miner()
