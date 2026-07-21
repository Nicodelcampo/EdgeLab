import pandas as pd
import numpy as np
from numba import njit, prange
import pyarrow.parquet as pq
import time

@njit(parallel=True, cache=True)
def run_strict_simulator(
    es_times, es_prices, es_bid, es_ask, es_vol,
    z_impact, z_upper, z_lower, z_dir
):
    n_zones = len(z_impact)
    
    classification = np.full(n_zones, 0, dtype=np.int8) 
    trade_pnl_ticks = np.full(n_zones, np.nan)
    
    time_5d_us = 5 * 24 * 3600 * 1000000
    time_15m_us = 900 * 1000000
    
    for k in prange(n_zones):
        t_imp = z_impact[k]
        d = z_dir[k] 
        
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
                    
        # 2. Simulador Cronologico Estricto (Cruzar Spread, SL/TP Rigidos)
        # Entry (Market Order)
        if d == 1: # Soporte, Buscamos Comprar
            entry_price = es_ask[idx_es] # Pagamos el spread (peor precio)
            tp_price = entry_price + 5.0 # 20 ticks arriba
            sl_price = entry_price - 5.0 # 20 ticks abajo
        else:      # Resistencia, Buscamos Vender
            entry_price = es_bid[idx_es] # Pagamos el spread (peor precio)
            tp_price = entry_price - 5.0 # 20 ticks abajo
            sl_price = entry_price + 5.0 # 20 ticks arriba
            
        idx_end_max = np.searchsorted(es_times, t_imp + time_15m_us)
        if idx_end_max >= len(es_times): idx_end_max = len(es_times) - 1
        
        closed = False
        pnl = 0.0
        
        for j in range(idx_es + 1, idx_end_max):
            if d == 1: # Trade Comprado
                # Para salir ganando, el BID debe subir a nuestro TP (Garantiza fill del limite)
                if es_bid[j] >= tp_price:
                    pnl = 20.0
                    closed = True
                    break
                # Para salir perdiendo, si el BID baja a nuestro SL, se dispara market sell
                if es_bid[j] <= sl_price:
                    pnl = -20.0
                    closed = True
                    break
            else: # Trade Vendido
                # Para salir ganando, el ASK debe bajar a nuestro TP (Garantiza fill)
                if es_ask[j] <= tp_price:
                    pnl = 20.0
                    closed = True
                    break
                # Para salir perdiendo, si el ASK sube a nuestro SL, dispara market buy
                if es_ask[j] >= sl_price:
                    pnl = -20.0
                    closed = True
                    break
                    
        if not closed:
            # Cierre por tiempo a Mercado
            if d == 1:
                pnl = (es_bid[idx_end_max] - entry_price) / 0.25
            else:
                pnl = (entry_price - es_ask[idx_end_max]) / 0.25
                
        trade_pnl_ticks[k] = pnl
            
    return classification, trade_pnl_ticks

def main():
    print("Iniciando Simulador Estricto Cronológico (Gauntlet)...")
    zones = pd.read_csv(r"C:\$AVectorBTecosistema\ES_zones.csv")
    first_touches = [int(str(x).split("|")[0])*1000 if pd.notna(x) and str(x).strip()!="" else -1 for x in zones["touch_ts_list"]]
    zones["t1_us"] = first_touches
    zones = zones[zones["t1_us"] > 0].copy().sort_values("t1_us").reset_index(drop=True)
    
    print("Cargando ES Ticks (148.8M rows)...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "bid", "ask", "volume"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    es_b = tbl_es.column("bid").to_numpy(zero_copy_only=False).astype(np.float64)
    es_a = tbl_es.column("ask").to_numpy(zero_copy_only=False).astype(np.float64)
    es_v = tbl_es.column("volume").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Simulacion de Ejecucion Realista...")
    t0 = time.time()
    cls_arr, pnl = run_strict_simulator(
        es_t, es_p, es_b, es_a, es_v,
        zones["t1_us"].values, zones["upper"].values, zones["lower"].values, zones["direction"].values
    )
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    df = pd.DataFrame({
        "Profile": cls_arr,
        "PnL_Ticks": pnl
    }).fillna(0)
    
    # Train / Test split (70% IS, 30% OOS)
    split_idx = int(len(df) * 0.7)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    def print_report(data, label):
        print(f"\n========== REPORTE {label} ==========")
        hvn = data[data["Profile"] == 1]
        lvn = data[data["Profile"] == -1]
        
        # Un trade es ganador si PnL > 0 (Idealmente +20 ticks si toco TP)
        wr_hvn = (hvn["PnL_Ticks"] > 0).mean()
        wr_lvn = (lvn["PnL_Ticks"] > 0).mean()
        
        print(f"Zonas HVN (Alta Densidad) : {len(hvn)} | Zonas LVN (Vacios) : {len(lvn)}")
        
        print("\n--- Desempeno Estricto Cruzando Spread (Tick a Tick) ---")
        print(f"Win Rate en HVN : {wr_hvn:.1%} | Expectancy: {hvn['PnL_Ticks'].mean():+.2f} ticks por trade")
        print(f"Win Rate en LVN : {wr_lvn:.1%} | Expectancy: {lvn['PnL_Ticks'].mean():+.2f} ticks por trade")
        
        if lvn['PnL_Ticks'].mean() > 0:
            print(">>> ESTADO LVN: EL EDGE ES REAL Y REPLICABLE. SOBREVIVE LA FRICCION.")
        else:
            print(">>> ESTADO LVN: EL EDGE ERA UNA ILUSION DEL MAE/MFE. DESTRUIDO POR FRICCION Y CRONOLOGIA.")
            
    print_report(train, "IN-SAMPLE (Primeros 5 Meses)")
    print_report(test, "OUT-OF-SAMPLE (Ultimos 2 Meses invisibles)")

if __name__ == "__main__":
    main()
