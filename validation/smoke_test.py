"""Smoke test del gauntlet (F2): una estrategia ALEATORIA (entradas random,
hold a EOD, mismos costos) debe MORIR en todas las pruebas:
  - expectancy neta <= 0 (los costos se la comen)
  - MCPT p ~ uniforme (>> 0.05)
  - PBO ~ 0.5 sobre una familia de 20 seeds random
Si algo de esto "pasa", el gauntlet esta roto y NO debe usarse.

Ejecutar:  python -m validation.smoke_test
"""
import sys
import numpy as np
import pandas as pd

from edgelab.config import ES_M1
from edgelab.sessions import rth_matrices, valid_days_mask
from validation.mcpt import mcpt
from validation.pbo import pbo_cscv
from validation.gauntlet import report

TICK = 0.25
COST_RT = 2.5


def random_trades(O, C, valid, seed):
    rng = np.random.RandomState(seed)
    nd, nm = O.shape
    pnl = []; days = []
    for d in range(nd):
        if not valid[d]:
            continue
        row_ok = np.flatnonzero(~np.isnan(C[d]))
        if len(row_ok) < 60:
            continue
        last = row_ok[-1]
        for _ in range(2):
            m = rng.randint(1, max(last - 10, 2))
            if np.isnan(O[d, m]):
                continue
            dr = 1 if rng.rand() < 0.5 else -1
            pnl.append(dr * (C[d, last] - O[d, m]) / TICK - COST_RT)
            days.append(d)
    return np.array(pnl), np.array(days, dtype=np.int64)


def make_pipeline(seed):
    def pipe(O, H, L, C, V):
        valid = valid_days_mask(O)
        pnl, _ = random_trades(O, C, valid, seed)
        return float(np.nansum(pnl))
    return pipe


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = pd.read_parquet(ES_M1)
    mats = rth_matrices(df)
    O, H, L, C, V = mats["O"], mats["H"], mats["L"], mats["C"], mats["V"]
    valid = valid_days_mask(O)
    print(f"dias validos: {valid.sum()}")

    pnl0, days0 = random_trades(O, C, valid, seed=0)
    day_ms = mats["days"].tz_localize(None).astype("int64").to_numpy() // 10**6
    times0 = day_ms[days0]

    print("\nMCPT sobre la estrategia random (200 perms)...")
    real, p, dist = mcpt(make_pipeline(0), O, H, L, C, V, n_perm=200, verbose=False)
    print(f"stat real={real:+.0f}t  p={p:.3f}  (esperado: p 'grande', no significativo)")

    # familia de 20 seeds -> matriz trades×combos alineada por dia para PBO
    n_seeds = 20
    per_day = {}
    for s in range(n_seeds):
        pnl_s, days_s = random_trades(O, C, valid, seed=s)
        dfd = pd.DataFrame({"d": days_s, "p": pnl_s}).groupby("d")["p"].sum()
        per_day[s] = dfd
    Rdf = pd.DataFrame(per_day).fillna(0.0)
    pbo = pbo_cscv(Rdf.to_numpy(), S=10)
    print(f"PBO familia random (20 seeds): {pbo['pbo']:.2f} de {pbo['n_splits']} splits "
          f"(esperado ~0.5)")

    report("SMOKE: estrategia random (debe morir)", pnl0, times0,
           mcpt_p=p, pbo=pbo["pbo"])


if __name__ == "__main__":
    main()
