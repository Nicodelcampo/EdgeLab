import pandas as pd
import numpy as np
from numba import njit
import pyarrow.parquet as pq
import time

@njit(cache=True)
def run_vwap_reversion(es_times, es_prices, es_bid, es_ask):
    N = len(es_times)
    sum_x = 0.0
    sum_x2 = 0.0
    count = 0
    left_idx = 0
    time_1h_us = 3600 * 1000000
    time_15m_us = 900 * 1000000
    
    trades_pnl = []
    trades_entry_ts = []
    trades_exit_ts = []
    trades_entry_px = []
    trades_exit_px = []
    trades_z = []
    trades_dir = []
    trades_reason = []
    
    in_trade = False
    trade_dir = 0
    entry_price = 0.0
    tp_price = 0.0
    sl_price = 0.0
    trade_start_idx = 0
    z_val = 0.0
    
    for right_idx in range(N):
        t = es_times[right_idx]
        p = es_prices[right_idx]
        
        sum_x += p
        sum_x2 += p * p
        count += 1
        
        while es_times[left_idx] < t - time_1h_us:
            p_old = es_prices[left_idx]
            sum_x -= p_old
            sum_x2 -= p_old * p_old
            count -= 1
            left_idx += 1
            
        if in_trade:
            # Check exit strictly crossing the spread
            closed = False
            pnl = 0.0
            exit_px = 0.0
            reason = 0 # 0=Time, 1=TP, -1=SL
            
            if trade_dir == 1: # Comprado
                if es_bid[right_idx] >= tp_price:
                    pnl = 20.0
                    exit_px = es_bid[right_idx]
                    reason = 1
                    closed = True
                elif es_bid[right_idx] <= sl_price:
                    pnl = -20.0
                    exit_px = es_bid[right_idx]
                    reason = -1
                    closed = True
            else: # Vendido
                if es_ask[right_idx] <= tp_price:
                    pnl = 20.0
                    exit_px = es_ask[right_idx]
                    reason = 1
                    closed = True
                elif es_ask[right_idx] >= sl_price:
                    pnl = -20.0
                    exit_px = es_ask[right_idx]
                    reason = -1
                    closed = True
                    
            if not closed and (t - es_times[trade_start_idx]) > time_15m_us:
                # Cierre por tiempo a Mercado
                if trade_dir == 1:
                    pnl = (es_bid[right_idx] - entry_price) / 0.25
                    exit_px = es_bid[right_idx]
                else:
                    pnl = (entry_price - es_ask[right_idx]) / 0.25
                    exit_px = es_ask[right_idx]
                reason = 0
                closed = True
                
            if closed:
                trades_pnl.append(pnl)
                trades_entry_ts.append(es_times[trade_start_idx])
                trades_exit_ts.append(t)
                trades_entry_px.append(entry_price)
                trades_exit_px.append(exit_px)
                trades_z.append(z_val)
                trades_dir.append(trade_dir)
                trades_reason.append(reason)
                in_trade = False
                
        else:
            if count > 1000:
                mean = sum_x / count
                var = (sum_x2 / count) - (mean * mean)
                if var > 0:
                    std = np.sqrt(var)
                    z = (p - mean) / std
                    
                    if z > 3.0: # Precio volo para arriba -> Reversion Corta (Vender al Bid)
                        in_trade = True
                        trade_dir = -1
                        entry_price = es_bid[right_idx]
                        tp_price = entry_price - 5.0 # TP 20 ticks
                        sl_price = entry_price + 5.0 # SL 20 ticks
                        trade_start_idx = right_idx
                        z_val = z
                        
                    elif z < -3.0: # Precio colapso -> Reversion Larga (Comprar al Ask)
                        in_trade = True
                        trade_dir = 1
                        entry_price = es_ask[right_idx]
                        tp_price = entry_price + 5.0
                        sl_price = entry_price - 5.0
                        trade_start_idx = right_idx
                        z_val = z
                        
    if in_trade:
        if trade_dir == 1:
            pnl = (es_bid[N-1] - entry_price) / 0.25
            exit_px = es_bid[N-1]
        else:
            pnl = (entry_price - es_ask[N-1]) / 0.25
            exit_px = es_ask[N-1]
        trades_pnl.append(pnl)
        trades_entry_ts.append(es_times[trade_start_idx])
        trades_exit_ts.append(es_times[N-1])
        trades_entry_px.append(entry_price)
        trades_exit_px.append(exit_px)
        trades_z.append(z_val)
        trades_dir.append(trade_dir)
        trades_reason.append(0)
        
    return trades_entry_ts, trades_exit_ts, trades_entry_px, trades_exit_px, trades_z, trades_dir, trades_reason, trades_pnl

def main():
    print("Iniciando Engine Validator (Control Positivo)...")
    
    print("Cargando ES Ticks (148.8M rows)...")
    tbl_es = pq.read_table(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "bid", "ask"])
    es_t = tbl_es.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[us]").astype(np.int64)
    es_p = tbl_es.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    es_b = tbl_es.column("bid").to_numpy(zero_copy_only=False).astype(np.float64)
    es_a = tbl_es.column("ask").to_numpy(zero_copy_only=False).astype(np.float64)
    
    print("Corriendo Simulador O(N) lineal sobre 148 millones de ticks...")
    t0 = time.time()
    ts_in, ts_out, px_in, px_out, z_list, dir_list, reason_list, pnl_list = run_vwap_reversion(es_t, es_p, es_b, es_a)
    print(f"Kernel finalizado en {time.time()-t0:.2f}s")
    
    df = pd.DataFrame({
        "Entry_Time": pd.to_datetime(ts_in, unit='us'),
        "Exit_Time": pd.to_datetime(ts_out, unit='us'),
        "Entry_Px": px_in,
        "Exit_Px": px_out,
        "Trade_Dir": dir_list,
        "Z_Score": z_list,
        "Reason": reason_list,
        "PnL_Ticks": pnl_list
    })
    
    if len(df) == 0:
        print("No se generaron trades.")
        return
        
    df.to_csv("suspicious_trades.csv", index=False)
    print("Exportado suspicious_trades.csv con data granular.")
    
    df["Win"] = df["PnL_Ticks"] > 0
    
    # Train / Test split (70% IS, 30% OOS) cronológico
    split_idx = int(len(df) * 0.7)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    def print_report(data, label):
        print(f"\n========== {label} ==========")
        print(f"Trades Generados : {len(data)}")
        
        if len(data) == 0: return
        
        wr = data["Win"].mean()
        exp = data["PnL_Ticks"].mean()
        
        print(f"Win Rate         : {wr:.1%}")
        print(f"Expectancy       : {exp:+.2f} ticks netos por trade")
        
        if exp > 0:
            print(">>> CONTROL POSITIVO CONFIRMADO. EL EDGE HA SOBREVIVIDO AL GAUNTLET ESTRICTO. <<<")
        else:
            print(">>> FALLO. EL MOTOR DESTRUYÓ INCLUSO UN EDGE CONOCIDO. <<<")

    print_report(train, "IN-SAMPLE (70% Historico)")
    print_report(test, "OUT-OF-SAMPLE (30% Futuro Invisible)")

if __name__ == "__main__":
    main()
