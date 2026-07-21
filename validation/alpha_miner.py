import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def extract_alpha_metrics(
    es_times, es_prices, 
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    
    # Hypotheses Metrics
    pacing_15s = np.full(n_zones, np.nan)
    sma_diff = np.full(n_zones, np.nan)
    
    # Outcomes a 15 mins
    mae = np.full(n_zones, np.nan)
    mfe = np.full(n_zones, np.nan)
    
    time_15m_us = 900 * 1000000
    time_15s_us = 15 * 1000000
    time_1h_us = 3600 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        d = z_dir[k] 
        
        idx_es = np.searchsorted(es_times, t_imp)
        if idx_es == 0 or idx_es >= len(es_times): continue
        
        # --- H2: Micro-Pacing (Ticks per second in last 15s) ---
        idx_es_15s = np.searchsorted(es_times, t_imp - time_15s_us)
        tick_count = idx_es - idx_es_15s
        pacing_15s[k] = tick_count / 15.0  # ticks per second
        
        # --- H4: Macro-Inertia (1h SMA Differential) ---
        idx_es_1h = np.searchsorted(es_times, t_imp - time_1h_us)
        if idx_es_1h < idx_es:
            # We can approximate SMA by taking a sample, but Numba loop is fast enough for 1h of ticks?
            # 1 hour of ES is about 50,000 ticks. Doing this 7,500 times is 375 million operations. Very fast.
            sum_p = 0.0
            for j in range(idx_es_1h, idx_es):
                sum_p += es_prices[j]
            sma = sum_p / (idx_es - idx_es_1h)
            sma_diff[k] = (es_prices[idx_es] - sma) / 0.25 # Diff in ticks
            
        # --- Outcomes a 15 mins ---
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
            
    return pacing_15s, sma_diff, mae, mfe

def main():
    print("Iniciando Alpha Miner Autónomo...")
    
    # 1. Cargar Zonas y derivar H1 (Zone Decay) y H3 (Double Tap)
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    
    t1_list = []
    t2_list = []
    for touch_str in zones["touch_ts_list"]:
        if pd.isna(touch_str) or str(touch_str).strip() == "":
            t1_list.append(-1)
            t2_list.append(-1)
        else:
            parts = str(touch_str).split("|")
            t1_list.append(int(parts[0]) * 1000) # a microsegundos
            if len(parts) > 1:
                t2_list.append(int(parts[1]) * 1000)
            else:
                t2_list.append(-1)
                
    zones["t1_us"] = t1_list
    zones["t2_us"] = t2_list
    
    # Filtrar válidas y ordenar
    zones = zones[zones["t1_us"] > 0].copy().sort_values("t1_us").reset_index(drop=True)
    
    # H1: Zone Decay (en minutos)
    zones["decay_mins"] = (zones["t1_us"] - zones["start_ts"]*1000) / (60 * 1000000)
    
    # H3: Double Tap Gap (en segundos)
    zones["double_tap_sec"] = np.where(zones["t2_us"] > 0, (zones["t2_us"] - zones["t1_us"]) / 1000000, -1)
    
    print("Cargando ES Ticks (148.8M rows)...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Kernel Numba de Macro-Inercia y Pacing...")
    t0 = time.time()
    pacing, sma_diff, mae, mfe = extract_alpha_metrics(
        es_t, es_p, 
        zones["t1_us"].values, zones["upper"].values, zones["lower"].values, zones["direction"].values
    )
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    df = pd.DataFrame({
        "dir": zones["direction"].values,
        "decay": zones["decay_mins"].values,
        "pacing": pacing,
        "sma_diff": sma_diff,
        "mae": mae,
        "mfe": mfe
    }).fillna(0)
    
    # Filtro logico: decay no puede ser negativo
    df = df[df["decay"] >= 0]
    
    # Win condition: Fade successful
    df["win"] = (df["mfe"] >= 20) & (df["mae"] < 20)
    
    split_idx = int(len(df) * 0.7)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    print(f"\nDatos In-Sample: {len(train)} zonas | Out-Of-Sample: {len(test)} zonas")
    
    # Grid Search sobre Hipotesis
    # Probaremos:
    # 1. Decay: < 30m, < 60m, < 120m, > 120m (Zonas frescas vs rancias)
    # 2. Pacing: < 10 t/s (Lento), > 50 t/s (Rapido)
    # 3. Macro-Inertia: A favor de la tendencia (Para Resistencia, SMA_diff > 40 ticks, es decir el precio subio desde su media)
    
    decay_threshs = [15, 30, 60, 120, 240]
    pacing_threshs = [5, 10, 25, 50]
    sma_threshs = [0, 20, 40, 80] # Distancia en ticks a la SMA
    
    results = []
    
    print("Buscando Alpha en In-Sample...")
    
    for dec in decay_threshs:
        for pac in pacing_threshs:
            for sma in sma_threshs:
                # Hipotesis A: Zona Fresca + Pacing Rapido + A favor de tendencia SMA
                # Si dir = -1 (Resistencia), tendencia alcista extendida = sma_diff > sma (precio muy por encima de la media)
                mask_res = (train["dir"] == -1) & (train["decay"] < dec) & (train["pacing"] > pac) & (train["sma_diff"] > sma)
                mask_sup = (train["dir"] == 1) & (train["decay"] < dec) & (train["pacing"] > pac) & (train["sma_diff"] < -sma)
                filtered = train[mask_res | mask_sup]
                
                if len(filtered) >= 50:
                    wr = filtered["win"].mean()
                    exp = wr * 20 - (1-wr) * 20
                    results.append({"Hypothesis": "Fresca+Rapida+Extendido", "Decay": dec, "Pacing": pac, "SMA": sma, "Trades": len(filtered), "WR": wr, "Exp": exp})
                
                # Hipotesis B: Zona Rancia + Pacing Lento (Deriva) + Contra tendencia (Mean Reversion)
                mask_res_b = (train["dir"] == -1) & (train["decay"] > dec) & (train["pacing"] < pac) & (train["sma_diff"] < -sma)
                mask_sup_b = (train["dir"] == 1) & (train["decay"] > dec) & (train["pacing"] < pac) & (train["sma_diff"] > sma)
                filtered_b = train[mask_res_b | mask_sup_b]
                
                if len(filtered_b) >= 50:
                    wr_b = filtered_b["win"].mean()
                    exp_b = wr_b * 20 - (1-wr_b) * 20
                    results.append({"Hypothesis": "Rancia+Lenta+Retorno", "Decay": dec, "Pacing": pac, "SMA": sma, "Trades": len(filtered_b), "WR": wr_b, "Exp": exp_b})

    if not results:
        print("Ninguna combinacion arrojo +50 trades. Saliendo.")
        return
        
    res_df = pd.DataFrame(results).sort_values("Exp", ascending=False)
    
    print("\n--- TOP 3 HIPOTESIS IN-SAMPLE ---")
    print(res_df.head(3).to_string(index=False))
    
    print("\nVerificando Mesetas (Robustez)...")
    robust = []
    for idx, row in res_df.iterrows():
        # Vecindario para decay +- 15m, pacing +- 10, sma +- 20
        d, p, s = row["Decay"], row["Pacing"], row["SMA"]
        h = row["Hypothesis"]
        
        mask_adj = (res_df["Hypothesis"] == h) & (res_df["Decay"].between(d-20, d+20)) & \
                   (res_df["Pacing"].between(p-15, p+15)) & (res_df["SMA"].between(s-30, s+30))
        
        vecindario = res_df[mask_adj]
        if len(vecindario) >= 3 and vecindario["Exp"].min() > 0:
            robust.append(row)
            if len(robust) >= 3: break
            
    if not robust:
        print("FRACASO: Ninguna hipotesis supero el filtro de Meseta (Overfitting Detectado).")
        return
        
    rob_df = pd.DataFrame(robust)
    print("\n--- TOP 3 HIPOTESIS ROBUSTAS ---")
    for idx, row in rob_df.iterrows():
        print(f"[{row['Hypothesis']}] Decay:{row['Decay']}m | Pacing:{row['Pacing']}t/s | SMA:{row['SMA']}t -> WR: {row['WR']:.1%} (Exp: {row['Exp']:.2f})")
        
    print("\n--- TEST OUT-OF-SAMPLE (EL FUTURO) ---")
    best = rob_df.iloc[0]
    dec, pac, sma = best["Decay"], best["Pacing"], best["SMA"]
    
    if best["Hypothesis"] == "Fresca+Rapida+Extendido":
        m_r = (test["dir"] == -1) & (test["decay"] < dec) & (test["pacing"] > pac) & (test["sma_diff"] > sma)
        m_s = (test["dir"] == 1) & (test["decay"] < dec) & (test["pacing"] > pac) & (test["sma_diff"] < -sma)
    else:
        m_r = (test["dir"] == -1) & (test["decay"] > dec) & (test["pacing"] < pac) & (test["sma_diff"] < -sma)
        m_s = (test["dir"] == 1) & (test["decay"] > dec) & (test["pacing"] < pac) & (test["sma_diff"] > sma)
        
    test_f = test[m_r | m_s]
    
    if len(test_f) == 0:
        print("0 trades en OOS.")
        return
        
    wr_test = test_f["win"].mean()
    exp_test = wr_test * 20 - (1-wr_test) * 20
    
    print(f"Trades OOS generados: {len(test_f)}")
    print(f"Expectancy OOS: {exp_test:+.2f} ticks")
    print(f"Win Rate OOS  : {wr_test:.1%}")
    if exp_test > 0:
        print("\n>>> SANTO GRIAL ENCONTRADO: LA HIPOTESIS SOBREVIVIO AL OUT-OF-SAMPLE. <<<")
    else:
        print("\n>>> FRACASO: LA HIPOTESIS TAMBIEN COLAPSO EN OOS. <<<")

if __name__ == "__main__":
    main()
