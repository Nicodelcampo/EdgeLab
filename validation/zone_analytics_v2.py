import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time
import os

@njit(parallel=True, cache=True)
def run_v2_analytics(
    es_times, es_prices, es_bid, es_ask, es_vol,
    nq_times, nq_prices,
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    n_es = len(es_times)
    n_nq = len(nq_times)
    
    # Outputs
    nq_vel = np.full(n_zones, np.nan, dtype=np.float64)
    ofi_5s = np.full(n_zones, np.nan, dtype=np.float64)
    
    # Breakout and pullback tracking
    is_breakout = np.zeros(n_zones, dtype=np.int8)
    is_pullback = np.zeros(n_zones, dtype=np.int8)
    
    # Horizon constants
    time_2h_us = 7200 * 1000000 
    time_60s_us = 60 * 1000000
    time_5s_us = 5 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        direction = z_dir[k] # -1 res, 1 sup
        
        idx_es = np.searchsorted(es_times, t_imp)
        idx_nq = np.searchsorted(nq_times, t_imp)
        
        if idx_es >= n_es or idx_nq >= n_nq or idx_es == 0 or idx_nq == 0:
            continue
            
        # 1. NQ Cross-Market Velocity (60s prior)
        idx_nq_60s = np.searchsorted(nq_times, t_imp - time_60s_us)
        if idx_nq_60s < idx_nq:
            # Distancia en ticks (Asumimos NQ tick size = 0.25)
            dist_nq = (nq_prices[idx_nq] - nq_prices[idx_nq_60s]) / 0.25
            nq_vel[k] = dist_nq # Positivo si subio, Negativo si bajo
            
        # 2. ES Micro-OFI (5s prior)
        idx_es_5s = np.searchsorted(es_times, t_imp - time_5s_us)
        if idx_es_5s < idx_es:
            delta = 0.0
            for j in range(idx_es_5s, idx_es):
                p = es_prices[j]
                b = es_bid[j]
                a = es_ask[j]
                v = es_vol[j]
                if p >= a:
                    delta += v
                elif p <= b:
                    delta -= v
            ofi_5s[k] = delta
            
        # 3. Pullback Tracker (2 horas forward)
        # Determinar si hay ruptura (penetrar > 10 puntos = 40 ticks)
        idx_end_2h = np.searchsorted(es_times, t_imp + time_2h_us)
        if idx_end_2h > n_es: idx_end_2h = n_es
        
        broken = False
        broken_idx = -1
        
        for j in range(idx_es, idx_end_2h):
            p = es_prices[j]
            # Si es resistencia (dir=-1), breakout es hacia arriba
            if direction == -1:
                if p - z_upper[k] >= 10.0: # 10 pts
                    broken = True
                    broken_idx = j
                    break
            else:
                # Si es soporte (dir=1), breakout es hacia abajo
                if z_lower[k] - p >= 10.0:
                    broken = True
                    broken_idx = j
                    break
                    
        if broken:
            is_breakout[k] = 1
            # Rastrear Pullback: Escanear el resto del tiempo hasta 2h a ver si toca la zona
            for j in range(broken_idx + 1, idx_end_2h):
                p = es_prices[j]
                if direction == -1:
                    # Breakout alcista. Pullback es caer hasta z_upper
                    if p <= z_upper[k]:
                        is_pullback[k] = 1
                        break
                else:
                    # Breakout bajista. Pullback es subir hasta z_lower
                    if p >= z_lower[k]:
                        is_pullback[k] = 1
                        break
                        
    return nq_vel, ofi_5s, is_breakout, is_pullback


def main():
    print("Iniciando Motor Analitico Intermercado v2...")
    
    # 1. Cargar Zonas
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = []
    for touch_str in zones["touch_ts_list"]:
        if pd.isna(touch_str) or str(touch_str).strip() == "":
            first_touches.append(-1)
        else:
            parts = str(touch_str).split("|")
            # Convertimos ms a us (microsegundos) para el timestamp
            first_touches.append(int(parts[0]) * 1000) 
            
    zones["first_touch_us"] = np.array(first_touches, dtype=np.int64)
    zones = zones[zones["first_touch_us"] > 0].copy()
    
    z_impact = zones["first_touch_us"].values.astype(np.int64)
    z_upper = zones["upper"].values.astype(np.float64)
    z_lower = zones["lower"].values.astype(np.float64)
    z_dir = zones["direction"].values.astype(np.int64)
    
    # 2. Cargar Cinta ES
    print("Cargando matriz ES (148.8M rows)...")
    t0 = time.time()
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", 
                           columns=["timestamp", "last", "bid", "ask", "volume"])
    es_times = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_prices = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    es_bid = tbl_es.column("bid").to_numpy(zero_copy_only=False).astype(np.float64)
    es_ask = tbl_es.column("ask").to_numpy(zero_copy_only=False).astype(np.float64)
    es_vol = tbl_es.column("volume").to_numpy(zero_copy_only=False).astype(np.float64)
    print(f"ES cargado en {time.time()-t0:.1f}s")
    
    # 3. Cargar Cinta NQ
    print("Cargando matriz NQ (Cientos de millones de rows)...")
    t0 = time.time()
    tbl_nq = pq.read_table(r"C:\$AVectorBTecosistema\NQ_ticks.parquet", 
                           columns=["timestamp", "price"])
    nq_times = tbl_nq.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    nq_prices = tbl_nq.column("price").to_numpy(zero_copy_only=False).astype(np.float64)
    print(f"NQ cargado en {time.time()-t0:.1f}s")
    
    # 4. Lanzar Motor Numba
    print("\nEjecutando kernel de sincronizacion cuantica (ES x NQ)...")
    t0 = time.time()
    nq_vel, ofi, breaks, pulls = run_v2_analytics(
        es_times, es_prices, es_bid, es_ask, es_vol,
        nq_times, nq_prices,
        z_impact, z_upper, z_lower, z_dir
    )
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    res = pd.DataFrame({
        "Direction": z_dir,
        "NQ_Velocity": nq_vel,
        "OFI_5s": ofi,
        "Breakout": breaks,
        "Pullback": pulls
    }).dropna()
    
    print("\n========== REPORTE DE PREDICTIBILIDAD v2 (MATRIZ INTERMERCADO) ==========\n")
    print(f"Zonas procesadas: {len(res):,}\n")
    
    # Micro-OFI
    print("--- 1. Order Flow Imbalance (5 segs pre-impacto) ---")
    res_resistencia = res[res["Direction"] == -1]
    res_soporte = res[res["Direction"] == 1]
    ofi_res = res_resistencia["OFI_5s"].median()
    ofi_sup = res_soporte["OFI_5s"].median()
    print(f"Delta mediano al golpear Resistencias : {ofi_res:+.0f} contratos")
    print(f"Delta mediano al golpear Soportes     : {ofi_sup:+.0f} contratos")
    print("  -> Si el delta se agota contra la zona (divergencia), predice absorcion.\n")
    
    # Matriz NQ
    print("--- 2. Matriz NQ (Cross-Asset Confirmation) ---")
    # Zonas de soporte (dir=1): Rebote ocurre si precio sube. Si NQ baja violento, mala senal.
    vel_res_median = res_resistencia["NQ_Velocity"].median()
    vel_sup_median = res_soporte["NQ_Velocity"].median()
    print(f"Inercia NQ al impactar Resistencias ES : {vel_res_median:+.1f} ticks/min")
    print(f"Inercia NQ al impactar Soportes ES     : {vel_sup_median:+.1f} ticks/min")
    print("  -> Cruce: Cuando el ES golpea zona, el NQ revela el estado global de la liquidez HFT.\n")
    
    # Pullbacks
    print("--- 3. Probabilidad Estadistica de Retesteo (Pullbacks) ---")
    total_breaks = res["Breakout"].sum()
    total_pulls = res["Pullback"].sum()
    if total_breaks > 0:
        pct = (total_pulls / total_breaks) * 100
        print(f"Rupturas Violentas Detectadas (>10pts) : {total_breaks:,}")
        print(f"Pullbacks exitosos a la frontera       : {total_pulls:,} ({pct:.1f}%)")
        print("  -> Conclusion: No persigas el precio tras la ruptura estructural.")
        print(f"     Tenes un {pct:.1f}% de probabilidades de que el precio vuelva al punto de origen.")
    else:
        print("Sin suficientes rupturas detectadas de esta magnitud.")

if __name__ == "__main__":
    main()
