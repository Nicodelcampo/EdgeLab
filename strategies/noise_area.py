"""Intraday Momentum "Noise Area" (Zarattini/Aziz/Barbon, SSRN 4824172) —
implementacion CAUSAL pre-registrada, EdgeLab F4/F5.

Reglas (fijadas ANTES de correr, sin grilla):
  - sigma(d,m) = media de |C(d',m)/O(d',0) - 1| de los ultimos 14 dias RTH
    validos previos (min 10). Point-in-time.
  - Bandas: UB = max(open, prev_close)*(1+sigma), LB = min(open, prev_close)*(1-sigma).
  - Entrada SOLO en HH:00/HH:30 (10:00..15:30 ET): si C(m-1) > UB(m-1) -> long;
    si C(m-1) < LB(m-1) -> short. Reversal permitido en esos chequeos.
  - Trailing (cada minuto): long sale si C(m-1) < max(LB(m-1), VWAP(m-1));
    short si C(m-1) > min(UB(m-1), VWAP(m-1)). VWAP de sesion RTH, minuto cerrado.
  - Flat al cierre RTH. Sin overnight. 1 contrato.
  - TODA decision usa la barra m-1; TODA ejecucion es al open de la barra m
    (regla 7 del cerebro: causalidad intrabar).
  - COSTO pre-registrado: 2.5 ticks round-trip (1t slippage por lado + 0.5t fees).

Auditoria: gauntlet completo con MCPT (500 permutaciones por-sesion re-corriendo
el pipeline entero, sigma incluida), IS/OOS 70/30, corte mensual. Config UNICA
(sin PBO por diseño; la multiplicidad la controla el MCPT a nivel pipeline).

Ejecutar:  python -m strategies.noise_area [ES|NQ]
"""
import sys
import numpy as np
import pandas as pd
from numba import njit

from edgelab.config import ES_M1, NQ_M1_CLEAN
from edgelab.sessions import rth_matrices, valid_days_mask
from validation.mcpt import mcpt
from validation.gauntlet import report

TICK = 0.25
COST_RT = 2.5          # ticks round-trip, pre-registrado
SIGMA_DAYS = 14
SIGMA_MIN_DAYS = 10
CHECK_MS = np.array([m for m in range(30, 361, 30)], dtype=np.int64)  # 10:00..15:30


def sigma_matrix(O, C, valid):
    """sigma(d,m) point-in-time: media de |C(d',m)/O(d',0)-1| de los ultimos
    SIGMA_DAYS dias validos ANTERIORES a d (NaN si < SIGMA_MIN_DAYS)."""
    nd, nm = C.shape
    move = np.abs(C / O[:, [0]] - 1.0)
    sig = np.full((nd, nm), np.nan)
    hist = []
    for d in range(nd):
        if len(hist) >= SIGMA_MIN_DAYS:
            block = np.array(hist[-SIGMA_DAYS:])
            sig[d] = np.nanmean(block, axis=0)
        if valid[d]:
            hist.append(move[d])
    return sig


@njit(cache=True)
def noise_area_kernel(O, H, L, C, V, prev_close, sig, valid, check_ms, cost_rt, tick):
    nd, nm = O.shape
    max_tr = nd * 16
    t_day = np.full(max_tr, -1, np.int64)
    t_dir = np.zeros(max_tr, np.int64)
    t_pnl = np.full(max_tr, np.nan)
    t_entry_m = np.full(max_tr, -1, np.int64)
    k = 0
    for d in range(nd):
        if not valid[d] or np.isnan(prev_close[d]) or np.isnan(sig[d, 0]):
            continue
        o0 = O[d, 0]
        ub_base = max(o0, prev_close[d])
        lb_base = min(o0, prev_close[d])
        pos = 0; entry = 0.0; entry_m = -1
        cum_pv = 0.0; cum_v = 0.0
        vwap_prev = np.nan
        last_m = -1
        for m in range(nm):
            if not np.isnan(C[d, m]):
                last_m = m
        if last_m < 60:
            continue
        for m in range(1, last_m + 1):
            cm1 = C[d, m - 1]
            if np.isnan(cm1):
                continue
            # actualizar VWAP con la barra m-1 (cerrada)
            hlc3 = (H[d, m - 1] + L[d, m - 1] + C[d, m - 1]) / 3.0
            vv = V[d, m - 1] if not np.isnan(V[d, m - 1]) else 0.0
            cum_pv += hlc3 * vv; cum_v += vv
            vwap_prev = cum_pv / cum_v if cum_v > 0 else np.nan
            om = O[d, m]
            if np.isnan(om):
                continue
            ub = ub_base * (1.0 + sig[d, m - 1])
            lb = lb_base * (1.0 - sig[d, m - 1])
            if np.isnan(ub) or np.isnan(lb):
                continue
            # --- exits por trailing (cada minuto) ---
            if pos == 1:
                trail = lb if np.isnan(vwap_prev) else max(lb, vwap_prev)
                if cm1 < trail:
                    t_day[k] = d; t_dir[k] = 1; t_entry_m[k] = entry_m
                    t_pnl[k] = (om - entry) / tick - cost_rt; k += 1
                    pos = 0
            elif pos == -1:
                trail = ub if np.isnan(vwap_prev) else min(ub, vwap_prev)
                if cm1 > trail:
                    t_day[k] = d; t_dir[k] = -1; t_entry_m[k] = entry_m
                    t_pnl[k] = (entry - om) / tick - cost_rt; k += 1
                    pos = 0
            # --- entradas/reversals solo en chequeos de media hora ---
            is_check = False
            for c in check_ms:
                if m == c:
                    is_check = True
                    break
            if is_check:
                if cm1 > ub and pos <= 0:
                    if pos == -1:
                        t_day[k] = d; t_dir[k] = -1; t_entry_m[k] = entry_m
                        t_pnl[k] = (entry - om) / tick - cost_rt; k += 1
                    pos = 1; entry = om; entry_m = m
                elif cm1 < lb and pos >= 0:
                    if pos == 1:
                        t_day[k] = d; t_dir[k] = 1; t_entry_m[k] = entry_m
                        t_pnl[k] = (om - entry) / tick - cost_rt; k += 1
                    pos = -1; entry = om; entry_m = m
        # --- EOD flat ---
        if pos != 0:
            xc = C[d, last_m]
            t_day[k] = d; t_dir[k] = pos; t_entry_m[k] = entry_m
            t_pnl[k] = pos * (xc - entry) / tick - cost_rt; k += 1
    return t_day[:k], t_dir[:k], t_pnl[:k], t_entry_m[:k]


def pipeline(O, H, L, C, V):
    """Pipeline completo (para MCPT): recomputa prev_close y sigma desde las
    matrices y corre el kernel. Devuelve el PnL neto TOTAL en ticks."""
    valid = valid_days_mask(O)
    nd = O.shape[0]
    last_close = np.full(nd, np.nan)
    for i in range(nd):
        row = C[i]; ok = ~np.isnan(row)
        if ok.any():
            last_close[i] = row[np.flatnonzero(ok)[-1]]
    prev_close = np.full(nd, np.nan)
    prev = np.nan
    for i in range(nd):
        prev_close[i] = prev
        if not np.isnan(last_close[i]):
            prev = last_close[i]
    sig = sigma_matrix(O, C, valid)
    _, _, pnl, _ = noise_area_kernel(O, H, L, C, V, prev_close, sig, valid,
                                     CHECK_MS, COST_RT, TICK)
    return float(np.nansum(pnl))


def run(symbol="ES", n_perm=500):
    src = ES_M1 if symbol == "ES" else NQ_M1_CLEAN
    tv = 12.5 if symbol == "ES" else 5.0
    df = pd.read_parquet(src)
    mats = rth_matrices(df)
    O, H, L, C, V = mats["O"], mats["H"], mats["L"], mats["C"], mats["V"]
    valid = valid_days_mask(O)
    sig = sigma_matrix(O, C, valid)
    print(f"{symbol}: {O.shape[0]} dias ET, validos {valid.sum()}, "
          f"con sigma {np.sum(~np.isnan(sig[:, 0]) & valid)}")

    td, tdir, tpnl, tem = noise_area_kernel(O, H, L, C, V, mats["prev_close"],
                                            sig, valid, CHECK_MS, COST_RT, TICK)
    day_ms = mats["days"].tz_localize(None).astype("int64").to_numpy() // 10**6
    times = day_ms[td]
    print(f"trades: {len(tpnl)} | brutos {np.nansum(tpnl) + COST_RT*len(tpnl):+.0f}t "
          f"| netos {np.nansum(tpnl):+.0f}t (${np.nansum(tpnl)*tv:+,.0f}) "
          f"| long {int((tdir==1).sum())} short {int((tdir==-1).sum())}")

    print(f"\nMCPT ({n_perm} permutaciones, pipeline completo)...")
    real, p, dist = mcpt(pipeline, O, H, L, C, V, n_perm=n_perm)
    print(f"stat real={real:+.0f}t | media perm={np.mean(dist):+.0f}t "
          f"p90 perm={np.quantile(dist, 0.9):+.0f}t | p={p:.4f}")

    res = report(f"Noise Area {symbol} (config unica pre-registrada, costo {COST_RT}t RT)",
                 tpnl, times, mcpt_p=p,
                 extra=f"long/short: {int((tdir==1).sum())}/{int((tdir==-1).sum())} | "
                       f"trades/dia={len(tpnl)/max(valid.sum(),1):.2f}")
    return {"pnl": tpnl, "times": times, "dir": tdir, "day": td, "entry_m": tem,
            "days": mats["days"], "res": res}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sym = sys.argv[1] if len(sys.argv) > 1 else "ES"
    run(sym)
