import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def run_bubble_miner(
    es_times, es_prices, es_vol, 
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    
    classification = np.full(n_zones, 0, dtype=np.int8) 
    bubbles = np.full(n_zones, 0.0, dtype=np.float64)
    
    time_5d_us = 5 * 24 * 3600 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        
        idx_es = np.searchsorted(es_times, t_imp)
        if idx_es == 0 or idx_es >= len(es_times): continue
        
        idx_start = np.searchsorted(es_times, t_imp - time_5d_us)
        
        # 1. HVN / LVN Profile
        hist = np.zeros(80000, dtype=np.float64)
        for j in range(idx_start, idx_es):
            px_tick = int(es_prices[j] * 4.0)
            if px_tick < 80000:
                hist[px_tick] += es_vol[j]
                
        active_nodes = []
        for v in hist:
            if v > 0:
                active_nodes.append(v)
                
        if len(active_nodes) > 10:
            arr_nodes = np.array(active_nodes)
            arr_nodes.sort() 
            p25 = arr_nodes[int(len(arr_nodes) * 0.25)]
            p75 = arr_nodes[int(len(arr_nodes) * 0.75)]
            
            z_px = (z_upper[k] + z_lower[k]) / 2.0
            z_tick = int(z_px * 4.0)
            if z_tick < 80000:
                z_vol = hist[z_tick]
                if z_vol >= p75: classification[k] = 1 # HVN
                elif z_vol <= p25: classification[k] = -1 # LVN
                    
        # 2. Bubble Calculation (Absorbed Volume in the first 60 seconds)
        abs_vol = 0.0
        time_60s_us = 60 * 1000000
        idx_end_60s = np.searchsorted(es_times, t_imp + time_60s_us)
        if idx_end_60s > len(es_times): idx_end_60s = len(es_times)
        
        for j in range(idx_es, idx_end_60s):
            p = es_prices[j]
            v = es_vol[j]
            if p >= z_lower[k] and p <= z_upper[k]:
                abs_vol += v
                
        bubbles[k] = abs_vol
            
    return classification, bubbles

def main():
    print("Iniciando Escaner de Burbujas de Absorcion (Footprint)...")
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = [int(str(x).split("|")[0])*1000 if pd.notna(x) and str(x).strip()!="" else -1 for x in zones["touch_ts_list"]]
    zones["t1_us"] = first_touches
    zones = zones[zones["t1_us"] > 0].copy().sort_values("t1_us").reset_index(drop=True)
    
    print("Cargando ES Ticks (148.8M rows)...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "volume"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    es_v = tbl_es.column("volume").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Kernel Numba (Vol Profile + Bubbles)...")
    t0 = time.time()
    cls_arr, bubbles = run_bubble_miner(
        es_t, es_p, es_v,
        zones["t1_us"].values, zones["upper"].values, zones["lower"].values, zones["direction"].values
    )
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    df = pd.DataFrame({
        "Profile": cls_arr, # 1: HVN, -1: LVN
        "Bubbles": bubbles
    })
    
    hvn_zones = df[df["Profile"] == 1]
    lvn_zones = df[df["Profile"] == -1]
    
    print("\n========== REPORTE DE ABSORCION (BURBUJAS) ==========\n")
    print("Volumen Mediano absorbido antes de que el precio escape de la zona:")
    print(f"Burbujas en HVN (Alta Densidad) : {hvn_zones['Bubbles'].median():.0f} contratos puros")
    print(f"Burbujas en LVN (Valles/Vacios) : {lvn_zones['Bubbles'].median():.0f} contratos puros")
    
    print("\nVolumen de Pánico (Top 20% de Burbujas Masivas):")
    print(f"Burbuja Extrema HVN : > {hvn_zones['Bubbles'].quantile(0.80):.0f} contratos")
    print(f"Burbuja Extrema LVN : > {lvn_zones['Bubbles'].quantile(0.80):.0f} contratos")
    
    # Check if there is a statistical difference
    if hvn_zones['Bubbles'].median() > lvn_zones['Bubbles'].median():
        print("\n-> Conclusion: En HVN la pelea es mucho mas sangrienta. Los limit orders absorben una cantidad inmensa de volumen antes de ceder.")
    else:
        print("\n-> Conclusion: En LVN se generan las mayores burbujas. El vacio se llena de pánico.")

if __name__ == "__main__":
    main()
