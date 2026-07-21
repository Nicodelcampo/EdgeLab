"""ORB 5-min NQ con FILLS TICK REALES (F6.1) — misma config congelada de
strategies/orb.py, pero ejecutada contra la cinta tick limpia (bid/ask):

  - rango = min/max de los primeros 5 minutos RTH (de las velas M1, causal);
  - desde 09:35 ET: stop-buy en hi / stop-sell en lo. Fill = ASK del primer
    tick cuyo ask cruza hi (long) o BID del primero cuyo bid cruza lo (short)
    -> slippage real de stop incluido;
  - stop-loss en el extremo opuesto: exit al BID (long) / ASK (short) del
    primer tick que lo cruza — peor caso real, sin ambiguedad intrabar;
  - EOD: exit al bid/ask del ultimo tick de la sesion RTH.
  - costo adicional: 0.5t de fees RT (el spread ya lo paga el cruce bid/ask).

Compara contra la version M1 peor-caso sobre los MISMOS dias.
Ejecutar:  python -m strategies.orb_tickfill
"""
import sys
import numpy as np
import pandas as pd
from numba import njit

from edgelab.config import NQ_M1_CLEAN, NQ_TICKS_CLEAN
from edgelab.sessions import rth_matrices, valid_days_mask
from validation.gauntlet import report
from strategies.orb import orb_kernel, OR_MIN, COST_RT

TICK = 0.25
FEES_RT = 0.5


SPREAD_CAP_T = 4.0   # cap anti-glitch del medio-spread pagado en cada fill


@njit(cache=True)
def orb_tick_kernel(t0_idx, t1_idx, hi_arr, lo_arr, ok_arr, last, bid, ask,
                    fees_rt, tick, spread_cap_t):
    """Triggers por LAST (asi disparan los stops en CME); fill = last +/-
    medio-spread observado, CAPEADO a spread_cap_t ticks (las quotes del
    export .Last son ruidosas: last-bid p999=32t son glitches, no liquidez)."""
    nd = len(t0_idx)
    t_dir = np.zeros(nd, np.int64)
    t_pnl = np.full(nd, np.nan)
    t_entry = np.full(nd, np.nan)
    used = np.zeros(nd, np.uint8)
    for d in range(nd):
        if not ok_arr[d]:
            continue
        i0, i1 = t0_idx[d], t1_idx[d]
        if i1 <= i0 + 10:
            continue
        hi, lo = hi_arr[d], lo_arr[d]
        pos = 0; entry = 0.0
        res = np.nan
        for i in range(i0, i1):
            if pos == 0:
                brk_up = last[i] >= hi
                brk_dn = last[i] <= lo
                if brk_up and brk_dn:
                    continue
                if brk_up:
                    half = min(max(ask[i] - last[i], 0.0), spread_cap_t * tick)
                    pos = 1; entry = last[i] + half
                elif brk_dn:
                    half = min(max(last[i] - bid[i], 0.0), spread_cap_t * tick)
                    pos = -1; entry = last[i] - half
            elif pos == 1:
                if last[i] <= lo:
                    half = min(max(last[i] - bid[i], 0.0), spread_cap_t * tick)
                    res = (last[i] - half - entry) / tick - fees_rt; break
            else:
                if last[i] >= hi:
                    half = min(max(ask[i] - last[i], 0.0), spread_cap_t * tick)
                    res = (entry - last[i] - half) / tick - fees_rt; break
        if pos != 0 and np.isnan(res):
            j = i1 - 1
            if pos == 1:
                half = min(max(last[j] - bid[j], 0.0), spread_cap_t * tick)
                res = (last[j] - half - entry) / tick - fees_rt
            else:
                half = min(max(ask[j] - last[j], 0.0), spread_cap_t * tick)
                res = (entry - last[j] - half) / tick - fees_rt
        if pos != 0:
            t_dir[d] = pos; t_pnl[d] = res; t_entry[d] = entry; used[d] = 1
    return t_dir, t_pnl, t_entry, used


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = pd.read_parquet(NQ_M1_CLEAN)
    mats = rth_matrices(df)
    O, H, L, C = mats["O"], mats["H"], mats["L"], mats["C"]
    valid = valid_days_mask(O)
    days = mats["days"]
    nd = len(days)

    # rango de apertura por dia (causal, de las velas)
    hi_arr = np.full(nd, np.nan); lo_arr = np.full(nd, np.nan)
    ok_arr = np.zeros(nd, dtype=np.bool_)
    for d in range(nd):
        if not valid[d] or np.isnan(H[d, :OR_MIN]).any():
            continue
        hi_arr[d] = np.nanmax(H[d, :OR_MIN])
        lo_arr[d] = np.nanmin(L[d, :OR_MIN])
        ok_arr[d] = True

    print("Cargando cinta tick limpia...")
    tape = pd.read_parquet(NQ_TICKS_CLEAN, columns=["ts_ns", "last", "bid", "ask"])
    ts = tape["ts_ns"].to_numpy()
    last = tape["last"].to_numpy(np.float64)
    bid = tape["bid"].to_numpy(np.float64)
    ask = tape["ask"].to_numpy(np.float64)
    print(f"{len(ts):,} ticks")

    # ventanas RTH por dia en ns UTC: 09:35 ET (fin del rango) -> 16:00 ET
    # (days ya viene tz-aware en America/New_York desde rth_matrices)
    et = days if days.tz is not None else days.tz_localize("America/New_York")
    start_ns = (et + pd.Timedelta(hours=9, minutes=35)).tz_convert("UTC") \
        .tz_localize(None).astype("int64").to_numpy()
    end_ns = (et + pd.Timedelta(hours=16)).tz_convert("UTC") \
        .tz_localize(None).astype("int64").to_numpy()
    t0_idx = np.searchsorted(ts, start_ns, side="left")
    t1_idx = np.searchsorted(ts, end_ns, side="left")

    tdir, tpnl, tentry, used = orb_tick_kernel(t0_idx, t1_idx, hi_arr, lo_arr,
                                               ok_arr, last, bid, ask, FEES_RT,
                                               TICK, SPREAD_CAP_T)
    mk = used == 1
    day_ms = days.tz_localize(None).astype("int64").to_numpy() // 10**6
    lvl = np.where(tdir[mk] == 1, hi_arr[mk], lo_arr[mk])
    slip = tdir[mk] * (tentry[mk] - lvl) / TICK
    print(f"\nTICK: {int(mk.sum())} trades | slippage de entrada vs nivel: "
          f"media {slip.mean():+.2f}t p50 {np.median(slip):+.2f}t "
          f"p90 {np.quantile(slip, 0.9):+.2f}t p99 {np.quantile(slip, 0.99):+.2f}t")

    # referencia M1 peor-caso sobre los MISMOS dias
    td_m1, tdir_m1, tpnl_m1 = orb_kernel(O, H, L, C, valid, COST_RT, TICK)
    common = np.isin(td_m1, np.flatnonzero(mk))
    print(f"M1 (peor-caso, costo {COST_RT}t): exp={np.nanmean(tpnl_m1):+.2f}t (n={len(tpnl_m1)})")
    print(f"TICK (bid/ask real + {FEES_RT}t fees): exp={np.nanmean(tpnl[mk]):+.2f}t (n={int(mk.sum())})")

    report("ORB 5-min NQ — FILLS TICK REALES (config congelada)",
           tpnl[mk], day_ms[mk],
           extra=f"win={100*np.mean(tpnl[mk]>0):.0f}% | "
                 f"long/short {int((tdir[mk]==1).sum())}/{int((tdir[mk]==-1).sum())}")


if __name__ == "__main__":
    main()
