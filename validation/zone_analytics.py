import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def run_zone_analytics(times, prices, z_impact, z_upper, z_lower, z_dir, time_horizon_ms):
    n_zones = len(z_impact)
    n_ticks = len(times)
    
    # Outputs
    mae = np.full(n_zones, np.nan, dtype=np.float64)
    mfe = np.full(n_zones, np.nan, dtype=np.float64)
    vel_approach = np.full(n_zones, np.nan, dtype=np.float64)
    time_in_zone = np.full(n_zones, np.nan, dtype=np.float64)
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        direction = z_dir[k] # -1 resistance, 1 support
        
        # Encontrar el indice de impacto usando biseccion (busqueda binaria rapida)
        # Numba soporta np.searchsorted
        idx = np.searchsorted(times, t_imp)
        if idx >= n_ticks or idx == 0:
            continue
            
        # 1. Approach Velocity (Ultimos 60 segs antes del impacto)
        idx_60s = np.searchsorted(times, t_imp - 60000000000)
        dist_approach = abs(prices[idx] - prices[idx_60s]) / 0.25
        vel_approach[k] = dist_approach # Ticks per minute
        
        # 2. Time in Zone (Milisegundos) & MAE/MFE a horizonte fijo
        t_end = t_imp + time_horizon_ms
        idx_end = np.searchsorted(times, t_end)
        if idx_end > n_ticks:
            idx_end = n_ticks
            
        max_px = prices[idx]
        min_px = prices[idx]
        left_zone_time = -1
        
        for j in range(idx, idx_end):
            p = prices[j]
            t = times[j]
            if p > max_px: max_px = p
            if p < min_px: min_px = p
            
            # Chequeo Time in Zone
            if left_zone_time == -1:
                # Si sale de la zona
                if p > z_upper[k] or p < z_lower[k]:
                    left_zone_time = (t - t_imp) / 1000000.0 # ms
                    
        if left_zone_time != -1:
            time_in_zone[k] = left_zone_time
        else:
            time_in_zone[k] = time_horizon_ms / 1000000.0 # no salio en el horizonte
            
        # MAE y MFE (Calculado en ticks)
        # Si es Resistencia (dir=-1), queremos que baje. 
        # Favorable (MFE) = min_px hacia abajo (z_lower - min_px). 
        # Adverso (MAE) = max_px hacia arriba (max_px - z_upper).
        if direction == -1:
            mfe[k] = (z_lower[k] - min_px) / 0.25
            mae[k] = (max_px - z_upper[k]) / 0.25
        else:
            # Si es Soporte (dir=1), queremos que suba.
            mfe[k] = (max_px - z_upper[k]) / 0.25
            mae[k] = (z_lower[k] - min_px) / 0.25
            
    return mae, mfe, vel_approach, time_in_zone


def main():
    print("Cargando Zonas Institucionales...")
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    
    # Extraer el PRIMER toque de cada zona
    first_touches = []
    for touch_str in zones["touch_ts_list"]:
        if pd.isna(touch_str) or str(touch_str).strip() == "":
            first_touches.append(-1)
        else:
            parts = str(touch_str).split("|")
            first_touches.append(int(parts[0]))
            
    zones["first_touch_ns"] = np.array(first_touches, dtype=np.int64) * 1000000 # asumiendo que esta en ms, pasar a ns
    # Validar que los timestamps del CSV esten alineados al parquet. Parquet es ns. 
    # El archivo dice 1778627610684 -> esto es Mayo 2026 en ms. Lo multiplicamos por 1 millon para ns.
    
    zones = zones[zones["first_touch_ns"] > 0].copy()
    
    print("Cargando Cinta de Ticks de Alta Frecuencia (148M rows)...")
    t0 = time.time()
    tbl = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last"])
    times = tbl.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[ns]").astype(np.int64)
    prices = tbl.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    print(f"Cinta lista en {time.time()-t0:.1f}s")
    
    # Extraer arrays para Numba
    z_impact = zones["first_touch_ns"].values.astype(np.int64)
    z_upper = zones["upper"].values.astype(np.float64)
    z_lower = zones["lower"].values.astype(np.float64)
    z_dir = zones["direction"].values.astype(np.int64)
    
    print("\nLanzando Motor Analitico (Zone Alpha Engine) sobre GPU/CPU-Cores...")
    t0 = time.time()
    # Horizonte de estudio: 15 minutos (900,000 ms)
    time_horizon_ms = 900000 * 1000000 
    
    mae, mfe, vel, tz = run_zone_analytics(times, prices, z_impact, z_upper, z_lower, z_dir, time_horizon_ms)
    print(f"Analisis Numba completado en {time.time()-t0:.2f}s")
    
    # Armar DataFrame de resultados
    res = pd.DataFrame({
        "MAE_ticks": mae,
        "MFE_ticks": mfe,
        "Velocity_tpm": vel,
        "TimeInZone_ms": tz,
        "Direction": z_dir
    }).dropna()
    
    print("\n========== REPORTE DE PREDICTIBILIDAD DE ZONAS (ES) ==========\n")
    print(f"Zonas procesadas y verificadas contra ticks: {len(res):,}\n")
    
    # 1. MAE / MFE
    print("--- 1. Perfil de Excursion a 15 Minutos ---")
    print(f"MFE Mediano (Favorable) : {res['MFE_ticks'].median():.1f} ticks")
    print(f"MAE Mediano (Adverso)   : {res['MAE_ticks'].median():.1f} ticks")
    print(f"Top 20% Rebotes (MFE)   : > {res['MFE_ticks'].quantile(0.80):.1f} ticks (Poder de reversion)")
    print(f"Top 20% Trampas (MAE)   : > {res['MAE_ticks'].quantile(0.80):.1f} ticks (Penetracion profunda)\n")
    
    # 2. Correlacion Velocidad -> Falla (Overshoot)
    print("--- 2. Velocidad de Impacto (Efecto Choque) ---")
    fast_zones = res[res["Velocity_tpm"] > res["Velocity_tpm"].quantile(0.80)]
    slow_zones = res[res["Velocity_tpm"] < res["Velocity_tpm"].quantile(0.20)]
    print(f"Penetracion Maxima (MAE) si el precio choca VELOZ (Top 20%): {fast_zones['MAE_ticks'].mean():.1f} ticks")
    print(f"Penetracion Maxima (MAE) si el precio deriva LENTO (Bot 20%): {slow_zones['MAE_ticks'].mean():.1f} ticks")
    if fast_zones['MAE_ticks'].mean() > slow_zones['MAE_ticks'].mean():
        print("  -> Conclusion: Impactos a alta velocidad penetran significativamente la zona (Overshoot).\n")
    
    # 3. Supervivencia de la Zona (Time-in-Zone)
    print("--- 3. Time-in-Zone (Absorcion vs Rechazo Rapido) ---")
    # Separar aquellas que fueron rebotes limpios (MFE > 16 ticks, MAE < 8 ticks) vs rupturas sucias
    rebotes = res[(res["MFE_ticks"] > 16) & (res["MAE_ticks"] < 8)]
    rupturas = res[res["MAE_ticks"] > 20]
    print(f"Tiempo dentro de la zona para Rebotes Limpios  : {rebotes['TimeInZone_ms'].median()/1000:.1f} segundos")
    print(f"Tiempo dentro de la zona antes de Rupturas     : {rupturas['TimeInZone_ms'].median()/1000:.1f} segundos")

if __name__ == "__main__":
    main()
