import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def run_volume_profile_miner(
    es_times, es_prices, es_vol, 
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    
    classification = np.full(n_zones, 0, dtype=np.int8) # -1 LVN, 0 Neutral, 1 HVN
    
    mae = np.full(n_zones, np.nan)
    mfe = np.full(n_zones, np.nan)
    time_in_zone = np.full(n_zones, np.nan)
    
    time_5d_us = 5 * 24 * 3600 * 1000000
    time_15m_us = 900 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        d = z_dir[k] 
        
        idx_es = np.searchsorted(es_times, t_imp)
        if idx_es == 0 or idx_es >= len(es_times): continue
        
        idx_start = np.searchsorted(es_times, t_imp - time_5d_us)
        
        # 1. Construir Perfil de Volumen (Histograma)
        # S&P 500 no superara 20000.00 pts pronto. 20000 * 4 = 80000 indices.
        hist = np.zeros(80000, dtype=np.float64)
        
        for j in range(idx_start, idx_es):
            px_tick = int(es_prices[j] * 4.0)
            if px_tick < 80000:
                hist[px_tick] += es_vol[j]
                
        # 2. Extraer percentiles de nodos activos
        active_nodes = []
        for v in hist:
            if v > 0:
                active_nodes.append(v)
                
        if len(active_nodes) > 10:
            arr_nodes = np.array(active_nodes)
            arr_nodes.sort() # Ordenar menor a mayor
            
            p25 = arr_nodes[int(len(arr_nodes) * 0.25)]
            p75 = arr_nodes[int(len(arr_nodes) * 0.75)]
            
            # 3. Evaluar la zona
            z_px = (z_upper[k] + z_lower[k]) / 2.0
            z_tick = int(z_px * 4.0)
            
            if z_tick < 80000:
                z_vol = hist[z_tick]
                if z_vol >= p75:
                    classification[k] = 1 # HVN
                elif z_vol <= p25:
                    classification[k] = -1 # LVN
                    
        # 4. Outcomes a 15 mins y Time-in-Zone
        idx_end = np.searchsorted(es_times, t_imp + time_15m_us)
        if idx_end > len(es_times): idx_end = len(es_times)
        
        max_p = es_prices[idx_es]
        min_p = es_prices[idx_es]
        left_zone_time = -1.0
        
        for j in range(idx_es, idx_end):
            p = es_prices[j]
            if p > max_p: max_p = p
            if p < min_p: min_p = p
            
            # Time in Zone
            if left_zone_time == -1.0:
                if p > z_upper[k] or p < z_lower[k]:
                    left_zone_time = (es_times[j] - t_imp) / 1000000.0 # ms
                    
        if left_zone_time != -1.0:
            time_in_zone[k] = left_zone_time
        else:
            time_in_zone[k] = time_15m_us / 1000000.0
            
        if d == -1:
            mfe[k] = (z_lower[k] - min_p) / 0.25
            mae[k] = (max_p - z_upper[k]) / 0.25
        else:
            mfe[k] = (max_p - z_upper[k]) / 0.25
            mae[k] = (z_lower[k] - min_p) / 0.25
            
    return classification, mae, mfe, time_in_zone


def main():
    print("Iniciando HVN vs LVN Profiler...")
    
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = [int(str(x).split("|")[0])*1000 if pd.notna(x) and str(x).strip()!="" else -1 for x in zones["touch_ts_list"]]
    zones["t1_us"] = first_touches
    zones = zones[zones["t1_us"] > 0].copy().sort_values("t1_us").reset_index(drop=True)
    
    print("Cargando ES Ticks (148.8M rows)...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "volume"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    es_v = tbl_es.column("volume").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Kernel Numba (Construyendo 7,500 Perfiles de Volumen de 5 dias en paralelo)...")
    t0 = time.time()
    cls_arr, mae, mfe, tiz = run_volume_profile_miner(
        es_t, es_p, es_v,
        zones["t1_us"].values, zones["upper"].values, zones["lower"].values, zones["direction"].values
    )
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    df = pd.DataFrame({
        "Profile": cls_arr, # 1: HVN, -1: LVN, 0: Neutral
        "MAE": mae,
        "MFE": mfe,
        "TimeInZone": tiz
    }).fillna(0)
    
    # Win condition: MAE < 20 ticks (5 pts), MFE >= 20 ticks (5 pts)
    df["Win"] = (df["MFE"] >= 20) & (df["MAE"] < 20)
    
    hvn_zones = df[df["Profile"] == 1]
    lvn_zones = df[df["Profile"] == -1]
    
    print("\n========== REPORTE ESTRUCTURAL: HVN vs LVN ==========\n")
    print(f"Zonas Analizadas: {len(df)}")
    print(f"Zonas en HVN (Alta Densidad) : {len(hvn_zones)}")
    print(f"Zonas en LVN (Valles/Vacios) : {len(lvn_zones)}")
    
    wr_hvn = hvn_zones["Win"].mean()
    wr_lvn = lvn_zones["Win"].mean()
    
    exp_hvn = wr_hvn * 20 - (1-wr_hvn) * 20
    exp_lvn = wr_lvn * 20 - (1-wr_lvn) * 20
    
    print("\n--- 1. Tasa de Rebote Exitoso (Fades) ---")
    print(f"Win Rate en HVN : {wr_hvn:.1%} (Expectancy: {exp_hvn:+.2f} ticks)")
    print(f"Win Rate en LVN : {wr_lvn:.1%} (Expectancy: {exp_lvn:+.2f} ticks)")
    
    print("\n--- 2. Comportamiento de Absorcion (Time-in-Zone) ---")
    # Tiz is in ms. Convert to seconds for readability
    print(f"Tiempo de resolucion mediano en HVN : {hvn_zones['TimeInZone'].median()/1000:.1f} segundos")
    print(f"Tiempo de resolucion mediano en LVN : {lvn_zones['TimeInZone'].median()/1000:.1f} segundos")
    
    print("\n--- 3. Perfil de Penetracion (MAE) ---")
    print(f"Penetracion mediana en contra de la zona (HVN) : {hvn_zones['MAE'].median():.1f} ticks")
    print(f"Penetracion mediana en contra de la zona (LVN) : {lvn_zones['MAE'].median():.1f} ticks")
    
    print("\n>>> CONCLUSION DE MICROESTRUCTURA <<<")
    if wr_lvn > wr_hvn and exp_lvn > 0:
        print("La Teoria de Subasta (Auction Market Theory) triunfa: Los LVN rechazan violentamente el precio. Fades rentables en LVN.")
    elif wr_hvn > wr_lvn and exp_hvn > 0:
        print("La Teoria de Muros HFT triunfa: Los HVN absorben toda la liquidez pasiva y hacen rebotar el precio. Fades rentables en HVN.")
    else:
        print("EMPATE NEUTRAL/NEGATIVO: Ambas zonas colapsan. El mercado eficiente destruye ambas hipotesis estructurales de volumen.")

if __name__ == "__main__":
    main()
