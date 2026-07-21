import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def extract_base_metrics(
    es_times, es_prices, es_bid, es_ask, es_vol,
    nq_times, nq_prices,
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    
    # 5 variables de OFI
    ofi_1s = np.full(n_zones, np.nan)
    ofi_2s = np.full(n_zones, np.nan)
    ofi_3s = np.full(n_zones, np.nan)
    ofi_5s = np.full(n_zones, np.nan)
    ofi_10s = np.full(n_zones, np.nan)
    
    # 4 variables de NQ Vel
    nq_10s = np.full(n_zones, np.nan)
    nq_30s = np.full(n_zones, np.nan)
    nq_60s = np.full(n_zones, np.nan)
    nq_120s = np.full(n_zones, np.nan)
    
    # Outcomes a 15 mins
    mae = np.full(n_zones, np.nan)
    mfe = np.full(n_zones, np.nan)
    
    time_15m_us = 900 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        d = z_dir[k] # -1 res, 1 sup
        
        idx_es = np.searchsorted(es_times, t_imp)
        idx_nq = np.searchsorted(nq_times, t_imp)
        if idx_es == 0 or idx_nq == 0 or idx_es >= len(es_times) or idx_nq >= len(nq_times): continue
        
        # OFI calcs
        for sec, arr in [(1, ofi_1s), (2, ofi_2s), (3, ofi_3s), (5, ofi_5s), (10, ofi_10s)]:
            idx_start = np.searchsorted(es_times, t_imp - sec * 1000000)
            delta = 0.0
            for j in range(idx_start, idx_es):
                p, b, a, v = es_prices[j], es_bid[j], es_ask[j], es_vol[j]
                if p >= a: delta += v
                elif p <= b: delta -= v
            arr[k] = delta
            
        # NQ calcs
        p_nq_imp = nq_prices[idx_nq]
        for sec, arr in [(10, nq_10s), (30, nq_30s), (60, nq_60s), (120, nq_120s)]:
            idx_start = np.searchsorted(nq_times, t_imp - sec * 1000000)
            if idx_start < idx_nq:
                # Ticks/min
                dist = (p_nq_imp - nq_prices[idx_start]) / 0.25
                arr[k] = dist * (60.0 / sec)
                
        # Outcomes
        idx_end = np.searchsorted(es_times, t_imp + time_15m_us)
        if idx_end > len(es_times): idx_end = len(es_times)
        
        max_p = es_prices[idx_es]
        min_p = es_prices[idx_es]
        for j in range(idx_es, idx_end):
            if es_prices[j] > max_p: max_p = es_prices[j]
            if es_prices[j] < min_p: min_p = es_prices[j]
            
        if d == -1:
            mfe[k] = (z_lower[k] - min_p) / 0.25
            mae[k] = (max_p - z_upper[k]) / 0.25
        else:
            mfe[k] = (max_p - z_upper[k]) / 0.25
            mae[k] = (z_lower[k] - min_p) / 0.25
            
    return ofi_1s, ofi_2s, ofi_3s, ofi_5s, ofi_10s, nq_10s, nq_30s, nq_60s, nq_120s, mae, mfe

def main():
    print("Iniciando Extraccion de Base...")
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = [int(str(x).split("|")[0])*1000 if pd.notna(x) and str(x).strip()!="" else -1 for x in zones["touch_ts_list"]]
    zones["first_touch_us"] = first_touches
    zones = zones[zones["first_touch_us"] > 0].copy()
    # Sort chronologically for IS/OOS split
    zones = zones.sort_values("first_touch_us").reset_index(drop=True)
    
    print("Cargando ES y NQ...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "bid", "ask", "volume"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p, es_b, es_a, es_v = [tbl_es.column(c).to_numpy(zero_copy_only=False).astype(np.float64) for c in ["last", "bid", "ask", "volume"]]
    
    tbl_nq = pq.read_table(r"C:\$AVectorBTecosistema\NQ_ticks.parquet", columns=["timestamp", "price"])
    nq_t = tbl_nq.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    nq_p = tbl_nq.column("price").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Kernel Numba de metricas...")
    res_arrays = extract_base_metrics(es_t, es_p, es_b, es_a, es_v, nq_t, nq_p, 
                         zones["first_touch_us"].values, zones["upper"].values, zones["lower"].values, zones["direction"].values)
    
    df = pd.DataFrame({
        "dir": zones["direction"].values,
        "ofi_1s": res_arrays[0], "ofi_2s": res_arrays[1], "ofi_3s": res_arrays[2], "ofi_5s": res_arrays[3], "ofi_10s": res_arrays[4],
        "nq_10s": res_arrays[5], "nq_30s": res_arrays[6], "nq_60s": res_arrays[7], "nq_120s": res_arrays[8],
        "mae": res_arrays[9], "mfe": res_arrays[10]
    }).fillna(0)
    
    # Objetivo: Ratio MFE/MAE o PnL simulado (TP 20 ticks, SL 20 ticks)
    df["win"] = (df["mfe"] >= 20) & (df["mae"] < 20)
    
    # Train / Test split (70% IS, 30% OOS)
    split_idx = int(len(df) * 0.7)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    print(f"\nDatos In-Sample: {len(train)} zonas | Out-Of-Sample: {len(test)} zonas")
    
    # Grid Search Parameters
    ofi_windows = ["ofi_1s", "ofi_2s", "ofi_3s", "ofi_5s", "ofi_10s"]
    nq_windows = ["nq_10s", "nq_30s", "nq_60s", "nq_120s"]
    ofi_threshs = [-150, -100, -50, 0, 50, 100]
    nq_threshs = [-30, -20, -10, 0, 10, 20]
    
    results = []
    
    print("Ejecutando Grid Search Vectorizado sobre In-Sample...")
    for o_win in ofi_windows:
        for n_win in nq_windows:
            for o_th in ofi_threshs:
                for n_th in nq_threshs:
                    # Filtro de divergencia estructural (para resistencias, delta se agota y nq frena)
                    # Normalizamos la direccion:
                    # Para ganar, queremos que el NQ y el OFI esten en CONTRA del movimiento hacia la zona.
                    # Si d=-1 (Resistencia, precio sube): OFI < o_th, NQ < n_th
                    # Si d=1 (Soporte, precio baja): OFI > -o_th, NQ > -n_th
                    
                    mask_res = (train["dir"] == -1) & (train[o_win] < o_th) & (train[n_win] < n_th)
                    mask_sup = (train["dir"] == 1) & (train[o_win] > -o_th) & (train[n_win] > -n_th)
                    filtered = train[mask_res | mask_sup]
                    
                    if len(filtered) < 50: continue # Insignificante estadisticamente
                    
                    wr = filtered["win"].mean()
                    expectancy = wr * 20 - (1-wr) * 20 # Simple net ticks expected
                    
                    results.append({
                        "ofi_win": o_win, "nq_win": n_win, "ofi_th": o_th, "nq_th": n_th,
                        "trades_IS": len(filtered), "wr_IS": wr, "exp_IS": expectancy
                    })
                    
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values("exp_IS", ascending=False)
    
    print("\n--- TOP 3 COMBINACIONES IN-SAMPLE (Candidatos al Overfit) ---")
    print(res_df.head(3).to_string(index=False))
    
    # 3. Parameter Stability (Plateau Check)
    print("\nEjecutando Filtro de Meseta de Estabilidad (Anti-Overfitting)...")
    robust_candidates = []
    for idx, row in res_df.head(100).iterrows():
        # Para que sea un plateau, sus variaciones adyacentes de umbral (o_th +- 50, n_th +- 10) deben ser rentables
        o_th, n_th = row["ofi_th"], row["nq_th"]
        adj_mask = (res_df["ofi_win"] == row["ofi_win"]) & (res_df["nq_win"] == row["nq_win"]) & \
                   (res_df["ofi_th"].between(o_th - 50, o_th + 50)) & (res_df["nq_th"].between(n_th - 10, n_th + 10))
        
        neighborhood = res_df[adj_mask]
        if len(neighborhood) >= 4 and neighborhood["exp_IS"].min() > 0:
            robust_candidates.append(row)
            if len(robust_candidates) >= 3: break
            
    if not robust_candidates:
        print("CUIDADO: Ningun set de parametros sobrevivio a la prueba de meseta. Todo era ruido (overfitting).")
        return
        
    rob_df = pd.DataFrame(robust_candidates)
    
    print("\n--- TOP 3 PARAMETROS ROBUSTOS (Superaron Prueba de Meseta) ---")
    for idx, row in rob_df.iterrows():
        print(f"OFI: {row['ofi_win']} (<{row['ofi_th']}) | NQ: {row['nq_win']} (<{row['nq_th']}) -> Exp_IS: {row['exp_IS']:.2f} ticks (WR {row['wr_IS']:.1%})")
        
    # 4. Out-of-Sample Verification (La Verdad)
    print("\n--- PRUEBA FINAL: OUT-OF-SAMPLE (Datos Futuros Invisibles) ---")
    best_row = rob_df.iloc[0]
    o_win, n_win, o_th, n_th = best_row["ofi_win"], best_row["nq_win"], best_row["ofi_th"], best_row["nq_th"]
    
    mask_res_test = (test["dir"] == -1) & (test[o_win] < o_th) & (test[n_win] < n_th)
    mask_sup_test = (test["dir"] == 1) & (test[o_win] > -o_th) & (test[n_win] > -n_th)
    test_filtered = test[mask_res_test | mask_sup_test]
    
    wr_test = test_filtered["win"].mean()
    exp_test = wr_test * 20 - (1-wr_test) * 20
    
    print(f"El mejor set robusto fue aplicado a los datos Out-of-Sample ({len(test_filtered)} trades generados).")
    print(f"Expectancy OOS: {exp_test:+.2f} ticks")
    print(f"Win Rate OOS  : {wr_test:.1%}")
    if exp_test > 0:
        print(">>> VEREDICTO: EL ALPHA HA SOBREVIVIDO. EL SET ES ROBUSTO. <<<")
    else:
        print(">>> VEREDICTO: DESTRUCCION OOS. EL ALPHA ESTABA SOBREOPTIMIZADO. <<<")

if __name__ == "__main__":
    main()
