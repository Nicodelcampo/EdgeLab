#!/usr/bin/env python3
r"""NQ-CRUCE25-CLIMA — pre-registro docs/research/MANIFIESTO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md.
NO CORRER antes de la auditoría (pedido de Nico). Pensado para Kaggle (dataset edgelab-nq-nt8-2026q3-l2ctx).

    python tools/nq_cruce25_clima.py --bars DIR_VELAS_25T --labels l2_contexts_NQ_labels.parquet --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402
from edgelab.research.espejo_nulo import simulate_null  # noqa: E402

M, HZ, SEED, N_CTRL, TOD_WIN, CAP_SES, N_BOOT = 4, 150, 20260929, 3, 1800, 300, 2000
LEVELS = {"N3": (17, 20), "N4": (13, 25), "N5": (9, 30)}
XS = (0.25, 0.5, 0.75, 1.0)
CLIMAS = ("calm", "normal", "volatile", "toxic")
ROLL = "20260915"


def agg(h, l, c, v, t):
    n = len(c) // M * M
    return (h[:n].reshape(-1, M).max(1), l[:n].reshape(-1, M).min(1), c[:n].reshape(-1, M)[:, -1],
            v[:n].reshape(-1, M).sum(1), t[:n].reshape(-1, M)[:, -1])


def race(H, L, j, tgt, fail, s, end):
    for q in range(j + 1, end + 1):
        ht = (H[q] >= tgt) if s == 1 else (L[q] <= tgt)
        hf = (L[q] <= fail) if s == 1 else (H[q] >= fail)
        if ht and hf:
            return 0
        if ht:
            return 1
        if hf:
            return 0
    return 0


def vol_prev(C):
    d = np.abs(np.diff(C, prepend=C[0])); out = np.full(len(C), np.nan)
    for i in range(20, len(C)):
        out[i] = d[i - 20:i].std()
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--bars", required=True); ap.add_argument("--labels", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lab = pd.read_parquet(a.labels)
    lab = lab[lab["evaluation_eligible"].fillna(False) & lab["context_as_of_ok"].fillna(False)].sort_values("available_utc_us")
    eval_ses = set(lab["cme_session"].astype(str))
    lab_t = lab["available_utc_us"].to_numpy(np.int64); lab_c = lab["context_state"].astype(str).to_numpy()
    files = [f for f in sorted(Path(a.bars).glob("*.npz")) if f.stem in eval_ses]
    S = {}
    for f in files:
        z = np.load(f); h, l, c, v = (z[q].astype(float) for q in ("h", "l", "c", "v")); t = z["t"].astype(float)
        H, L, C, V, T = agg(h, l, c, v, t)
        o = np.r_[c[0], c[:-1]]
        S[f.stem] = dict(H=H, L=L, C=C, V=V, T=T, n=len(C), vol=vol_prev(C), trip=np.column_stack([c - o, h - o, l - o]))
    allv = np.concatenate([D["vol"][~np.isnan(D["vol"])] for D in S.values()]); cut = np.quantile(allv, [1 / 3, 2 / 3])
    ter = lambda x: -1 if np.isnan(x) else (0 if x <= cut[0] else (2 if x > cut[1] else 1))
    cand = [(s, q, D["T"][q] % 86400, ter(D["vol"][q])) for s, D in S.items() for q in range(20, D["n"] - 2)]
    cs = np.array([x[0] for x in cand]); cq = np.array([x[1] for x in cand]); ctod = np.array([x[2] for x in cand]); cter = np.array([x[3] for x in cand])
    rng = np.random.default_rng(SEED)
    out = {}
    for lvl, (mw, mb) in LEVELS.items():
        rows, sin_clima, sin_ctrl = [], 0, 0
        for s, D in S.items():
            n = D["n"]
            if n < 60:
                continue
            H, L, C, V, T = D["H"], D["L"], D["C"], D["V"], D["T"]
            res = K.run(T, np.r_[C[0], C[:-1]], H, L, C, V, np.zeros(n, int), params=dict(e_max=1.01, atr_k=None, min_w=float(mw), max_bars=mb))
            comp = [e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"]
            imps = {im["imp_id"]: im for im in res["impulses"]}
            if len(comp) > CAP_SES:
                comp = [comp[i] for i in np.sort(rng.choice(len(comp), CAP_SES, replace=False))]
            for e in comp:
                im = imps[e["imp_id"]]; k = e["bar"]; d = im["dir"]; A = im["A"]; W = im["W"]
                E = A; j = None
                for q in range(k, n - 1):
                    E = min(E, L[q]) if d == 1 else max(E, H[q])
                    if d * (C[q] - A) > 0:
                        j = q; break
                if j is None or not W:
                    continue
                end = min(j + HZ, n - 1)
                t_us = int(T[j] * 1e6)
                i = np.searchsorted(lab_t, t_us, side="right") - 1
                clima = lab_c[i] if i >= 0 and t_us - lab_t[i] <= 120_000_000 else None
                if clima is None:
                    sin_clima += 1; continue
                fail = E - d * 1; r = dict(session=s, clima=clima, post_roll=s >= ROLL, O=float(d * (A - E) / W), ev={}, ctrl={}, sint={})
                dt = np.abs(ctod - T[j] % 86400); dt = np.minimum(dt, 86400 - dt)
                idx = np.flatnonzero((cs != s) & (dt <= TOD_WIN) & (cter == ter(D["vol"][j])))
                if len(idx) < N_CTRL:
                    sin_ctrl += 1; continue
                ctrl_pick = rng.choice(idx, N_CTRL, replace=False)
                pool = D["trip"][:j * M]
                for x in XS:
                    tgt = A + d * x * W
                    r["ev"][str(x)] = race(H, L, j, tgt, fail, d, end)
                    hits = []
                    for ci in ctrl_pick:
                        Dc = S[cs[ci]]; q = int(cq[ci]); off_t = tgt - C[j]; off_f = fail - C[j]
                        hits.append(race(Dc["H"], Dc["L"], q, Dc["C"][q] + off_t, Dc["C"][q] + off_f, d, min(q + (end - j), Dc["n"] - 1)))
                    r["ctrl"][str(x)] = float(np.mean(hits))
                    if len(pool) >= 50:
                        seed = int(hashlib.sha256(f"{lvl}|{s}|{j}|{x}".encode()).hexdigest()[:8], 16)
                        r["sint"][str(x)] = simulate_null(C[j], tgt, fail, d, pool, end - j, n=300, seed=seed, bars_per_step=M)["completa"]
                rows.append(r)
        out[lvl] = dict(eventos=rows, sin_clima=sin_clima, sin_soporte_control=sin_ctrl)
        print(lvl, "eventos", len(rows), "sin clima", sin_clima, "sin control", sin_ctrl, flush=True)
    # pruebas primarias: x = 0,25, nivel × clima, diferencia pareada, bootstrap por sesión, max-T sobre 12
    cells, tn = [], []
    for lvl, O in out.items():
        for cl in CLIMAS:
            X = [r for r in O["eventos"] if r["clima"] == cl]
            if len(X) < 30:
                cells.append(dict(nivel=lvl, clima=cl, n=len(X), sin_potencia=True)); continue
            dd = np.array([r["ev"]["0.25"] - r["ctrl"]["0.25"] for r in X]); ses = np.array([r["session"] for r in X])
            u = np.unique(ses); ix = {x: i for i, x in enumerate(u)}; si = np.array([ix[x] for x in ses])
            Sm = np.zeros(len(u)); N = np.zeros(len(u)); np.add.at(Sm, si, dd); np.add.at(N, si, 1)
            Wb = np.random.default_rng(SEED + 7).multinomial(len(u), np.ones(len(u)) / len(u), size=N_BOOT).astype(float)
            bm = (Wb @ Sm) / np.maximum(Wb @ N, 1e-9); obs = dd.mean(); se = bm.std()
            tn.append(np.abs((bm - obs) / se))
            cells.append(dict(nivel=lvl, clima=cl, n=len(X), sesiones=len(u), llega_evento=float(np.mean([r["ev"]["0.25"] for r in X])),
                              llega_control=float(np.mean([r["ctrl"]["0.25"] for r in X])), dif=float(obs),
                              ic90=[float(np.quantile(bm, .05)), float(np.quantile(bm, .95))], t=float(obs / se), mde80=2.8 * float(se)))
    crit = float(np.quantile(np.max(np.vstack(tn).T, 1), .95)) if tn else None
    for c in cells:
        if "t" in c:
            c["sobrevive_maxT"] = abs(c["t"]) >= crit
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "nq_cruce25_clima.json").write_text(json.dumps(dict(t_critico=crit, primarias=cells, detalle=out), default=float), encoding="utf-8")
    for c in cells:
        print(c if "t" not in c else f"{c['nivel']} {c['clima']:8s} n {c['n']} evento {c['llega_evento']:.3f} control {c['llega_control']:.3f} dif {c['dif']:+.3f} {[round(v, 3) for v in c['ic90']]} t {c['t']:.2f} maxT {c['sobrevive_maxT']}")
    print("t crítico", crit)


if __name__ == "__main__":
    main()
