"""ORB 5-min (Opening Range Breakout) — comparativo Tier 3, prior BAJA
pre-registrada (el paper de Zarattini muestra Sharpe 0.48 SIN el filtro
"Stocks in Play", que no es portable a un futuro unico).

Reglas (config UNICA, sin grilla):
  - Rango = [min(L), max(H)] de los primeros 5 minutos RTH (09:30-09:34).
  - Desde 09:35: stop-buy en high del rango, stop-sell en low (ordenes
    apoyadas — causales). Primera que se ejecuta define la posicion (peor
    caso si la barra cruza ambos niveles: se asume SL primero despues de
    entrar; la entrada misma usa max(open, nivel) = fill realista de stop).
  - Stop-loss = extremo opuesto del rango. Sin TP: exit EOD o stop.
  - 1 trade por dia como maximo. Costo 2.5t RT.
Ejecutar:  python -m strategies.orb [ES|NQ]
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
COST_RT = 2.5
OR_MIN = 5


@njit(cache=True)
def orb_kernel(O, H, L, C, valid, cost_rt, tick):
    nd, nm = O.shape
    t_day = np.full(nd, -1, np.int64)
    t_dir = np.zeros(nd, np.int64)
    t_pnl = np.full(nd, np.nan)
    k = 0
    for d in range(nd):
        if not valid[d]:
            continue
        hi = -1e18; lo = 1e18
        ok = True
        for m in range(OR_MIN):
            if np.isnan(H[d, m]):
                ok = False; break
            hi = max(hi, H[d, m]); lo = min(lo, L[d, m])
        if not ok:
            continue
        last_m = -1
        for m in range(nm):
            if not np.isnan(C[d, m]):
                last_m = m
        if last_m <= OR_MIN:
            continue
        pos = 0; entry = 0.0
        res = np.nan
        for m in range(OR_MIN, last_m + 1):
            if np.isnan(H[d, m]):
                continue
            if pos == 0:
                brk_up = H[d, m] > hi
                brk_dn = L[d, m] < lo
                if brk_up and brk_dn:
                    # barra cruza ambos: peor caso = entra y sale stopeado
                    pos = 1; entry = max(O[d, m], hi)
                    res = (lo - entry) / tick - cost_rt
                    break
                elif brk_up:
                    pos = 1; entry = max(O[d, m], hi)
                elif brk_dn:
                    pos = -1; entry = min(O[d, m], lo)
            else:
                if pos == 1 and L[d, m] <= lo:
                    res = (lo - entry) / tick - cost_rt; break
                if pos == -1 and H[d, m] >= hi:
                    # BUG HISTORICO (cazado por la validacion tick F6.1): estaba
                    # escrito (hi - entry) — booking del stop del short como
                    # GANANCIA. Signo correcto: entry - hi (perdida).
                    res = (entry - hi) / tick - cost_rt; break
        if pos != 0 and np.isnan(res):
            res = pos * (C[d, last_m] - entry) / tick - cost_rt
        if pos != 0:
            t_day[k] = d; t_dir[k] = pos; t_pnl[k] = res; k += 1
    return t_day[:k], t_dir[:k], t_pnl[:k]


def pipeline(O, H, L, C, V):
    valid = valid_days_mask(O)
    _, _, pnl = orb_kernel(O, H, L, C, valid, COST_RT, TICK)
    return float(np.nansum(pnl))


def run(symbol="ES", n_perm=500):
    src = ES_M1 if symbol == "ES" else NQ_M1_CLEAN
    tv = 12.5 if symbol == "ES" else 5.0
    df = pd.read_parquet(src)
    mats = rth_matrices(df)
    O, H, L, C, V = mats["O"], mats["H"], mats["L"], mats["C"], mats["V"]
    valid = valid_days_mask(O)
    td, tdir, tpnl = orb_kernel(O, H, L, C, valid, COST_RT, TICK)
    day_ms = mats["days"].tz_localize(None).astype("int64").to_numpy() // 10**6
    times = day_ms[td]
    print(f"{symbol} ORB: {len(tpnl)} trades | netos {np.nansum(tpnl):+.0f}t "
          f"(${np.nansum(tpnl)*tv:+,.0f})")
    real, p, dist = mcpt(pipeline, O, H, L, C, V, n_perm=n_perm, verbose=False)
    print(f"MCPT: real={real:+.0f}t media_perm={np.mean(dist):+.0f}t p={p:.4f}")
    return report(f"ORB 5-min {symbol} (config unica, costo {COST_RT}t RT)",
                  tpnl, times, mcpt_p=p)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run(sys.argv[1] if len(sys.argv) > 1 else "ES")
