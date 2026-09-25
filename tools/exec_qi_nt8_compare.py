#!/usr/bin/env python3
r"""EXEC-QI, validación de fills: lee los CSV de EdgeLabExecQIProbe (NT8) y compara.
Protocolo: docs/research/PROTOCOLO_VALIDACION_EXEC_QI_NT8_20260924.md

1. Ahorro REALIZADO por el experimento aleatorizado: costo medio de A menos costo medio de P, por tercil de d·QI.
   Costo = d·(precio de fill − precio medio de la decisión), en ticks. Como política y dirección se sortean,
   la diferencia no tiene sesgo de selección.
2. Si existe el L2 de ese día (E:\l2_parquet\<base>), simula el modelo pesimista de `exec_qi.py` en los MISMOS
   instantes de las decisiones P y compara fill sí/no y precio. Eso mide cuán optimista o pesimista es cada motor
   (el de NT8 o el del prop) contra el nuestro.

    .venv\Scripts\python tools\exec_qi_nt8_compare.py --csv "C:\Users\...\EdgeLab\execqi\*.csv" [--base NQ_09-26]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import exec_qi as E  # noqa: E402
import nq_l2_explore as X  # noqa: E402

OUT = REPO / "artifacts" / "exec_qi_nt8"


def wall_us(s):
    """Hora de pared de NT8 (ART) -> la convención de los parquet L2 (pared ART guardada como UTC)."""
    t = pd.to_datetime(s.str.slice(0, 26), format="ISO8601")
    return ((t - pd.Timestamp(0)) // pd.Timedelta(microseconds=1)).to_numpy().astype(np.int64)   # independiente de la resolución


def boot_diff(a, p, sess_a, sess_p, seed=E.SEED):
    """Media(A) − media(P) con IC bootstrap por día."""
    days = sorted(set(sess_a) | set(sess_p))
    if len(days) < 2 or len(a) < 10 or len(p) < 10:
        return [float(np.mean(a) - np.mean(p)) if len(a) and len(p) else None, None, None, len(a), len(p)]
    r = np.random.default_rng(seed)
    A = {d: a[sess_a == d] for d in days}; P = {d: p[sess_p == d] for d in days}
    bs = []
    for _ in range(E.N_BOOT):
        k = r.choice(days, len(days))
        aa = np.concatenate([A[d] for d in k]); pp = np.concatenate([P[d] for d in k])
        if len(aa) and len(pp):
            bs.append(aa.mean() - pp.mean())
    return [float(a.mean() - p.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(a), len(p)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--base", help="carpeta L2 del contrato para la comparación con el modelo (p. ej. NQ_09-26)")
    a = ap.parse_args(argv)
    files = sorted(glob.glob(a.csv))
    D = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    D["tick"] = D.tick_size
    D["mid0"] = (D.bid + D.ask) / 2
    D["cost"] = D.dir * (D.fill_price - D.mid0) / D.tick                     # ticks, positivo = costo
    D["dqi"] = D.dir * D.qi
    D["qib"] = pd.cut(D.dqi, [-9, -E.QI_CUT, E.QI_CUT - 1e-12, 9], labels=["contra", "neutral", "a_favor"])
    D["day"] = D.decision_time.str.slice(0, 10)
    if D.day.nunique() < 5:                                   # con pocos días el bloque es la hora (declarado en el protocolo)
        D["day"] = D.decision_time.str.slice(0, 13)
    out = {"files": files, "n": int(len(D))}
    for acct, G in D.groupby("account"):
        res = {}
        for qb in ["contra", "neutral", "a_favor", "todos"]:
            g = G if qb == "todos" else G[G.qib == qb]
            A_, P_ = g[g.policy == "A"], g[g.policy == "P"]
            res[qb] = dict(ahorro=boot_diff(A_.cost.to_numpy(), P_.cost.to_numpy(), A_.day.to_numpy(), P_.day.to_numpy()),
                           fill_P_sin_cruzar=float(1 - P_.crossed_after_timeout.mean()) if len(P_) else None)
        out[acct] = res
        if a.base:
            base = Path(r"E:\l2_parquet") / a.base
            P_ = G.copy()                                            # todas las decisiones: el modelo evalúa A y P en cada una
            P_["t0"] = wall_us(P_.submit_time) + X.LAT
            rows = []
            for day, g in P_.groupby(P_.decision_time.str.slice(0, 10).str.replace("-", "")):
                if not (base / "l1_quotes" / f"{day}.parquet").exists():
                    continue
                X.BASE = base
                Q, T = X.load_l1(day)
                arr = (Q.ts.to_numpy(), Q.bid.to_numpy(), Q.ask.to_numpy(), Q.bsz.to_numpy().astype(float), Q.asz.to_numpy().astype(float),
                       T.ts.to_numpy(), T.px.to_numpy(), T.sz.to_numpy().astype(float), T.aggr.to_numpy())
                qts, qb, qa = arr[0], arr[1], arr[2]
                for _, r in g.iterrows():
                    d = int(r.dir)
                    pm, filled, _ = E.simulate_passive(*arr, int(r.t0), d, int(r.timeout_s), 1.0)
                    j = max(np.searchsorted(qts, int(r.t0), "right") - 1, 0)
                    pa = float(qa[j] if d == 1 else qb[j])
                    rows.append(dict(day=day, policy=r.policy, qib=r.qib, nt8_filled=int(1 - r.crossed_after_timeout), model_filled=filled,
                                     nt8_price_t=r.fill_price / r.tick, model_price_t=pm, model_A_t=pa, dir=d,
                                     model_save=d * (pa - pm)))
            if rows:
                M = pd.DataFrame(rows)
                MP, MA = M[M.policy == "P"], M[M.policy == "A"]
                out[acct + "_vs_modelo"] = dict(
                    n_P=len(MP), fill_nt8=float(MP.nt8_filled.mean()), fill_modelo=float(MP.model_filled.mean()),
                    acuerdo_fill=float((MP.nt8_filled == MP.model_filled).mean()),
                    P_nt8_menos_modelo_ticks=float((MP.dir * (MP.nt8_price_t - MP.model_price_t)).mean()),
                    A_nt8_menos_modelo_ticks=float((MA.dir * (MA.nt8_price_t - MA.model_A_t)).mean()),
                    ahorro_modelo_mismos_instantes={q: float(M.model_save[M.qib == q].mean()) for q in ["contra", "neutral", "a_favor"]}
                    | {"todos": float(M.model_save.mean())})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "compare.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, default=float)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
