import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.audit_gc_execution_falsification import audit_contract_causal, analyze_trade_set

data_dir = Path("E:/EdgeLab/data/nt8/GC_parquet")
contracts = ["GC 12-25", "GC 02-26", "GC 04-26", "GC 06-26"]

all_seq = []
for c in contracts:
    fname = c.replace(" ", "_") + "_ticks.parquet"
    f = data_dir / fname
    res = audit_contract_causal(f, c, ticks_per_bar=25, sl_mult=1.5, tp_pts=4.0)
    pnl_s = sum(t["pnl_usd"] for t in res["sequential_trades"])
    all_seq.extend(res["sequential_trades"])
    print(f"{c}: Seq Trades = {len(res['sequential_trades'])} | PnL = ${pnl_s:+,.2f}")

stats = analyze_trade_set(all_seq, "TP=4.0 pt | SL=1.5x (Secuencial Realista)")
print("\n=== TOTAL MULTI-CONTRATO TP=4.0 pt | SL=1.5x ===")
print(f"Trades: {stats['trades']} | Win%: {stats['win_rate']}% | PF: {stats['profit_factor']}")
print(f"PnL Total: ${stats['total_pnl_usd']:+,.2f} USD")
print(f"Max Drawdown: ${stats['max_drawdown_usd']:,.2f} USD | Max Losing Streak: {stats['max_losing_streak']} perdidas")
print(f"Longs: PnL = ${stats['long_pnl_usd']:+,.2f} (WR {stats['long_win_rate']}%) | Shorts: PnL = ${stats['short_pnl_usd']:+,.2f} (WR {stats['short_win_rate']}%)")
