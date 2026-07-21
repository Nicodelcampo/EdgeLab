import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def extract_zscore_metrics(
    es_times, es_prices, es_bid, es_ask, es_vol,
    nq_times, nq_prices,
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    
    ofi_z = np.full(n_zones, np.nan)
    nq_z = np.full(n_zones, np.nan)
    
    mae = np.full(n_zones, np.nan)
    mfe = np.full(n_zones, np.nan)
    
    time_15m_us = 900 * 1000000
    time_1h_us = 3600 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        d = z_dir[k] 
        
        idx_es = np.searchsorted(es_times, t_imp)
        idx_nq = np.searchsorted(nq_times, t_imp)
        if idx_es == 0 or idx_nq == 0 or idx_es >= len(es_times) or idx_nq >= len(nq_times): continue
        
        # --- 1. Calcular OFI_5s en el Impacto ---
        idx_es_5s = np.searchsorted(es_times, t_imp - 5000000)
        impact_ofi = 0.0
        for j in range(idx_es_5s, idx_es):
            p, b, a, v = es_prices[j], es_bid[j], es_ask[j], es_vol[j]
            if p >= a: impact_ofi += v
            elif p <= b: impact_ofi -= v
            
        # --- 2. Baseline OFI_5s (Ultima hora, muestreado cada 5s) ---
        samples_ofi = np.zeros(720)
        t_start_h = t_imp - time_1h_us
        
        idx_cursor = np.searchsorted(es_times, t_start_h)
        for i in range(720):
            t_win_end = t_start_h + (i+1) * 5000000
            idx_next = np.searchsorted(es_times, t_win_end)
            delta = 0.0
            for j in range(idx_cursor, idx_next):
                p, b, a, v = es_prices[j], es_bid[j], es_ask[j], es_vol[j]
                if p >= a: delta += v
                elif p <= b: delta -= v
            samples_ofi[i] = delta
            idx_cursor = idx_next
            
        mean_ofi = np.mean(samples_ofi)
        std_ofi = np.std(samples_ofi)
        if std_ofi > 0:
            ofi_z[k] = (impact_ofi - mean_ofi) / std_ofi
        else:
            ofi_z[k] = 0.0
            
        # --- 3. Calcular NQ_Vel_10s en el Impacto ---
        idx_nq_10s = np.searchsorted(nq_times, t_imp - 10000000)
        impact_nq_dist = 0.0
        if idx_nq_10s < idx_nq:
            impact_nq_dist = (nq_prices[idx_nq] - nq_prices[idx_nq_10s]) / 0.25
            
        # --- 4. Baseline NQ_Vel_10s (Ultima hora, muestreado cada 10s) ---
        samples_nq = np.zeros(360)
        t_nq_start_h = t_imp - time_1h_us
        idx_nq_cursor = np.searchsorted(nq_times, t_nq_start_h)
        
        for i in range(360):
            t_win_end = t_nq_start_h + (i+1) * 10000000
            idx_nq_next = np.searchsorted(nq_times, t_win_end)
            if idx_nq_cursor < idx_nq_next:
                samples_nq[i] = (nq_prices[idx_nq_next-1] - nq_prices[idx_nq_cursor]) / 0.25
            else:
                samples_nq[i] = 0.0
            idx_nq_cursor = idx_nq_next
            
        mean_nq = np.mean(samples_nq)
        std_nq = np.std(samples_nq)
        if std_nq > 0:
            nq_z[k] = (impact_nq_dist - mean_nq) / std_nq
        else:
            nq_z[k] = 0.0
            
        # --- 5. Outcomes a 15 mins ---
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
            
    return ofi_z, nq_z, mae, mfe


def main():
    print("Iniciando Extraccion Z-Score Adaptativo...")
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = [int(str(x).split("|")[0])*1000 if pd.notna(x) and str(x).strip()!="" else -1 for x in zones["touch_ts_list"]]
    zones["first_touch_us"] = first_touches
    zones = zones[zones["first_touch_us"] > 0].copy().sort_values("first_touch_us").reset_index(drop=True)
    
    print("Cargando ES y NQ...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "bid", "ask", "volume"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p, es_b, es_a, es_v = [tbl_es.column(c).to_numpy(zero_copy_only=False).astype(np.float64) for c in ["last", "bid", "ask", "volume"]]
    
    tbl_nq = pq.read_table(r"C:\$AVectorBTecosistema\NQ_ticks.parquet", columns=["timestamp", "price"])
    nq_t = tbl_nq.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    nq_p = tbl_nq.column("price").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Kernel Numba (Rolling Baseline 1h para cada impacto)...")
    t0 = time.time()
    ofi_z, nq_z, mae, mfe = extract_zscore_metrics(es_t, es_p, es_b, es_a, es_v, nq_t, nq_p, 
                         zones["first_touch_us"].values, zones["upper"].values, zones["lower"].values, zones["direction"].values)
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    df = pd.DataFrame({
        "dir": zones["direction"].values,
        "ofi_z": ofi_z, "nq_z": nq_z, "mae": mae, "mfe": mfe
    }).fillna(0)
    
    # Objetivo
    df["win"] = (df["mfe"] >= 20) & (df["mae"] < 20)
    
    # Train / Test split (70% IS, 30% OOS)
    split_idx = int(len(df) * 0.7)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    print(f"\nDatos In-Sample: {len(train)} zonas | Out-Of-Sample: {len(test)} zonas")
    
    # Grid Search Z-Scores
    z_threshs = [-2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0]
    
    results = []
    
    print("Ejecutando Grid Search de Z-Scores sobre In-Sample...")
    for o_th in z_threshs:
        for n_th in z_threshs:
            # Para ganar (divergencia), queremos Z-Scores negativos (agotamiento) en direccion al choque.
            mask_res = (train["dir"] == -1) & (train["ofi_z"] < o_th) & (train["nq_z"] < n_th)
            mask_sup = (train["dir"] == 1) & (train["ofi_z"] > -o_th) & (train["nq_z"] > -n_th)
            filtered = train[mask_res | mask_sup]
            
            if len(filtered) < 50: continue 
            
            wr = filtered["win"].mean()
            expectancy = wr * 20 - (1-wr) * 20 
            
            results.append({
                "ofi_z_th": o_th, "nq_z_th": n_th,
                "trades_IS": len(filtered), "wr_IS": wr, "exp_IS": expectancy
            })
            
    res_df = pd.DataFrame(results).sort_values("exp_IS", ascending=False)
    
    print("\n--- TOP 3 Z-SCORES IN-SAMPLE ---")
    print(res_df.head(3).to_string(index=False))
    
    # Plateau Check (Z-Score)
    print("\nEjecutando Filtro de Meseta Z-Score...")
    robust_candidates = []
    for idx, row in res_df.iterrows():
        o_th, n_th = row["ofi_z_th"], row["nq_z_th"]
        # Tolerancia de vecindario de 0.5 desviaciones estandar
        adj_mask = (res_df["ofi_z_th"].between(o_th - 0.51, o_th + 0.51)) & \
                   (res_df["nq_z_th"].between(n_th - 0.51, n_th + 0.51))
        neighborhood = res_df[adj_mask]
        if len(neighborhood) >= 4 and neighborhood["exp_IS"].min() > 0:
            robust_candidates.append(row)
            if len(robust_candidates) >= 3: break
            
    if not robust_candidates:
        print("OVERFITTING TOTAL: Ninguna meseta Z-Score sobrevivio.")
        return
        
    rob_df = pd.DataFrame(robust_candidates)
    
    print("\n--- TOP 3 Z-SCORES ROBUSTOS (Plateau OK) ---")
    for idx, row in rob_df.iterrows():
        print(f"OFI_Z < {row['ofi_z_th']} | NQ_Z < {row['nq_z_th']} -> Exp_IS: {row['exp_IS']:.2f} ticks (WR {row['wr_IS']:.1%})")
        
    # OOS Verification
    print("\n--- PRUEBA FINAL Z-SCORE: OUT-OF-SAMPLE (Futuro) ---")
    best_row = rob_df.iloc[0]
    o_th, n_th = best_row["ofi_z_th"], best_row["nq_z_th"]
    
    mask_res_test = (test["dir"] == -1) & (test["ofi_z"] < o_th) & (test["nq_z"] < n_th)
    mask_sup_test = (test["dir"] == 1) & (test["ofi_z"] > -o_th) & (test["nq_z"] > -n_th)
    test_filtered = test[mask_res_test | mask_sup_test]
    
    if len(test_filtered) == 0:
        print("No se generaron trades OOS. (Parametros demasiado estrictos)")
        return
        
    wr_test = test_filtered["win"].mean()
    exp_test = wr_test * 20 - (1-wr_test) * 20
    
    print(f"Mejor Z-Score aplicado OOS ({len(test_filtered)} trades generados).")
    print(f"Expectancy OOS: {exp_test:+.2f} ticks")
    print(f"Win Rate OOS  : {wr_test:.1%}")
    if exp_test > 0:
        print(">>> SUCESO INSTITUCIONAL: EL Z-SCORE HA SOBREVIVIDO AL FUTURO. ALPHA VALIDADO. <<<")
    else:
        print(">>> FRACASO OOS: El Z-Score tambien se rompio. Fin de la hipotesis. <<<")

if __name__ == "__main__":
    main()
