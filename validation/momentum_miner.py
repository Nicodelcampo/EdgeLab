import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def run_momentum_breakout_sim(
    es_times, es_prices, es_bid, es_ask,
    z_impact, z_dir,
    tp_target
):
    n_zones = len(z_impact)
    
    pacing_15s = np.full(n_zones, np.nan)
    trade_pnl_ticks = np.full(n_zones, np.nan)
    
    time_15s_us = 15 * 1000000
    time_15m_us = 900 * 1000000
    
    sl_target = 10.0 # 10 ticks (2.5 puntos) fijo para cortar perdedoras rapido
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        d = z_dir[k] 
        
        idx_es = np.searchsorted(es_times, t_imp)
        if idx_es == 0 or idx_es >= len(es_times): continue
        
        # 1. Pacing (Densidad de ticks en ultimos 15s)
        idx_es_15s = np.searchsorted(es_times, t_imp - time_15s_us)
        tick_count = idx_es - idx_es_15s
        pacing_15s[k] = tick_count / 15.0  # ticks por segundo
        
        # 2. Simulador Cronologico de Ruptura (Breakout)
        if d == -1: # Resistencia, esperamos que la ROMPA hacia ARRIBA -> Compramos (Buy Breakout)
            entry_price = es_ask[idx_es]
            tp_price = entry_price + tp_target 
            sl_price = entry_price - sl_target 
        else:      # Soporte, esperamos que la ROMPA hacia ABAJO -> Vendemos (Sell Breakout)
            entry_price = es_bid[idx_es]
            tp_price = entry_price - tp_target 
            sl_price = entry_price + sl_target 
            
        idx_end_max = np.searchsorted(es_times, t_imp + time_15m_us)
        if idx_end_max >= len(es_times): idx_end_max = len(es_times) - 1
        
        closed = False
        pnl = 0.0
        
        for j in range(idx_es + 1, idx_end_max):
            if d == -1: # Comprado (Buy Breakout)
                if es_bid[j] >= tp_price:
                    pnl = tp_target
                    closed = True
                    break
                if es_bid[j] <= sl_price:
                    pnl = -sl_target
                    closed = True
                    break
            else: # Vendido (Sell Breakout)
                if es_ask[j] <= tp_price:
                    pnl = tp_target
                    closed = True
                    break
                if es_ask[j] >= sl_price:
                    pnl = -sl_target
                    closed = True
                    break
                    
        if not closed:
            # Cierre por tiempo a Mercado
            if d == -1:
                pnl = (es_bid[idx_end_max] - entry_price) / 0.25
            else:
                pnl = (entry_price - es_ask[idx_end_max]) / 0.25
                
        trade_pnl_ticks[k] = pnl
            
    return pacing_15s, trade_pnl_ticks

def main():
    print("Iniciando Simulador Momentum (Breakouts)...")
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = [int(str(x).split("|")[0])*1000 if pd.notna(x) and str(x).strip()!="" else -1 for x in zones["touch_ts_list"]]
    zones["t1_us"] = first_touches
    zones = zones[zones["t1_us"] > 0].copy().sort_values("t1_us").reset_index(drop=True)
    
    print("Cargando ES Ticks (148.8M rows)...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "bid", "ask"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    es_b = tbl_es.column("bid").to_numpy(zero_copy_only=False).astype(np.float64)
    es_a = tbl_es.column("ask").to_numpy(zero_copy_only=False).astype(np.float64)
    
    tp_targets = [20.0, 30.0, 40.0] # 5 pts, 7.5 pts, 10 pts
    pacing_threshs = [10, 20, 30, 40, 50] # Ticks per second
    
    # Train / Test indices
    split_idx = int(len(zones) * 0.7)
    
    results = []
    
    print("Corriendo Simulaciones de Cuadricula en In-Sample (Cronologico estricto)...")
    
    for tp in tp_targets:
        # Corremos el simulador para este TP
        pacing, pnl = run_momentum_breakout_sim(
            es_t, es_p, es_b, es_a,
            zones["t1_us"].values, zones["direction"].values, tp
        )
        
        df = pd.DataFrame({"Pacing": pacing, "PnL": pnl})
        train = df.iloc[:split_idx]
        test = df.iloc[split_idx:]
        
        for pac in pacing_threshs:
            # Filtramos los trades con alta inercia
            filtered = train[train["Pacing"] >= pac]
            trades_count = len(filtered)
            
            if trades_count >= 50:
                wr = (filtered["PnL"] > 0).mean()
                exp = filtered["PnL"].mean()
                
                results.append({
                    "TP": tp, "Pacing": pac,
                    "Trades": trades_count, "WR": wr, "Exp": exp
                })
                
    if not results:
        print("Ninguna combinacion genero mas de 50 trades.")
        return
        
    res_df = pd.DataFrame(results).sort_values("Exp", ascending=False)
    print("\n--- TOP 3 COMBINACIONES IN-SAMPLE (Candidatos) ---")
    print(res_df.head(3).to_string(index=False))
    
    print("\nVerificando Mesetas de Momentum...")
    robust = []
    for idx, row in res_df.iterrows():
        tp = row["TP"]
        pac = row["Pacing"]
        
        # Vecindario de pacing
        mask_adj = (res_df["TP"] == tp) & (res_df["Pacing"].between(pac-11, pac+11))
        vecindario = res_df[mask_adj]
        
        if len(vecindario) >= 2 and vecindario["Exp"].min() > 0:
            robust.append(row)
            if len(robust) >= 3: break
            
    if not robust:
        print("FRACASO: Ninguna ruptura (Breakout) supero el filtro de Meseta.")
        return
        
    rob_df = pd.DataFrame(robust)
    print("\n--- TOP COMBINACIONES ROBUSTAS ---")
    for idx, row in rob_df.iterrows():
        print(f"TP:{row['TP']}t | Pacing > {row['Pacing']}t/s -> WR: {row['WR']:.1%} (Exp: {row['Exp']:.2f})")
        
    print("\n--- TEST OUT-OF-SAMPLE (EL FUTURO) ---")
    best = rob_df.iloc[0]
    best_tp, best_pac = best["TP"], best["Pacing"]
    
    _, pnl_oos = run_momentum_breakout_sim(
        es_t, es_p, es_b, es_a,
        zones["t1_us"].values, zones["direction"].values, best_tp
    )
    
    df_oos = pd.DataFrame({"Pacing": pacing, "PnL": pnl_oos})
    test_oos = df_oos.iloc[split_idx:]
    
    filtered_oos = test_oos[test_oos["Pacing"] >= best_pac]
    
    if len(filtered_oos) == 0:
        print("0 trades en OOS.")
        return
        
    wr_test = (filtered_oos["PnL"] > 0).mean()
    exp_test = filtered_oos["PnL"].mean()
    
    print(f"Trades OOS generados (Pacing > {best_pac}): {len(filtered_oos)}")
    print(f"Expectancy OOS: {exp_test:+.2f} ticks por trade")
    print(f"Win Rate OOS  : {wr_test:.1%}")
    
    if exp_test > 0:
        print("\n>>> SANTO GRIAL ENCONTRADO: LA HIPOTESIS DE RUPTURA SOBREVIVIO AL OUT-OF-SAMPLE. <<<")
    else:
        print("\n>>> FRACASO: LAS RUPTURAS TAMBIEN SON ARBITRADAS Y NO DAN ALPHA SOSTENIBLE. <<<")

if __name__ == "__main__":
    main()
