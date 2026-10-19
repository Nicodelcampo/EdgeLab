#!/usr/bin/env python3
r"""Control empírico del nulo de CONT/REV (pedido de Nico 28/09, Kaggle).

Para cada trade real (espejo completado) se toman 3 velas al azar de la MISMA sesión (≥ 50 velas lejos del evento) y se
repite la misma operación: misma dirección, mismo W, mismos TP/SL, misma distancia entre el cierre de la vela y el precio
de entrada. Se publican por celda TP/SL:
  1. calibración del nulo: media(R_azar − E0_azar) → debe ser ≈ 0 si simulate_null está bien calibrado;
  2. exceso con nulo: media(R_real − E0_real) (lo que reportaron CONT/REV);
  3. exceso empírico: media(R_real) − media(R_azar), sin modelo.
Casos: NQ continuación N4, ES continuación N3, GC reversión W100 (sin feb-2026). Tope 4.000 trades por caso (sorteo).

    python tools/espejo_null_control.py --case NQ_cont_N4 --bars DIR --out DIR
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

from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402
from edgelab.research.espejo_nulo import simulate_null  # noqa: E402

M, HZ, N_NULL, SEED, MAX_T, N_RAND = 4, 150, 300, 20260928, 4000, 3
TPS = (0.25, 0.5, 1.0, 1.5, 2.0); SLS = (0.25, 0.5, 1.0)
KEYS = [f"{tp}_{sl}" for tp in TPS for sl in SLS]
CASES = {"NQ_cont_N4": ("NQ", "cont", 13, 25, ()), "ES_cont_N3": ("ES", "cont", 17, 20, ()),
         "GC_rev_W100": ("GC", "rev", 100, 30, ("202602",))}


def agg(h, l, c):
    n = len(c) // M * M
    return h[:n].reshape(-1, M).max(1), l[:n].reshape(-1, M).min(1), c[:n].reshape(-1, M)[:, -1]


def trade(H, L, C, k, fill, c, tp, sl, end):
    T = fill + c * tp; S = fill - c * sl
    for j in range(k + 1, end + 1):
        if (L[j] <= S) if c == 1 else (H[j] >= S):
            return S
        if (H[j] >= T) if c == 1 else (L[j] <= T):
            return T
    return C[end]


def evaluate(H, L, C, trip, k, fill, cd, W, key, seedtag):
    """R y E0 (nulo desde el cierre de k) para las 15 celdas."""
    end = min(k + HZ, len(C) - 1)
    pool = trip[:k * M]
    if end <= k or len(pool) < 50:
        return None
    R, E = [], []
    for tp in TPS:
        for sl in SLS:
            px = trade(H, L, C, k, fill, cd, tp * W, sl * W, end); r = cd * (px - fill) / W
            seed = int(hashlib.sha256(f"{seedtag}|{k}|{tp}|{sl}".encode()).hexdigest()[:8], 16)
            p0 = simulate_null(C[k], fill + cd * tp * W, fill - cd * sl * W, cd, pool, end - k, n=N_NULL, seed=seed, bars_per_step=M)
            E.append(p0["completa"] * tp - (p0["falla"] + p0["ambigua"]) * sl + p0["censurada"] * cd * (C[k] - fill) / W); R.append(r)
    return np.array(R), np.array(E)


def run(case, bars_dir, out_dir):
    inst, mode, mw, mb, excl = CASES[case]
    files = [f for f in sorted(Path(bars_dir).glob("*.npz")) if not f.stem.startswith(excl or ("x",))]
    cands = []
    for f in files:
        z = np.load(f); h, l, c = (z[q].astype(float) for q in ("h", "l", "c")); t = z["t"].astype(float)
        H, L, C = agg(h, l, c); n = len(C)
        if n < 120:
            continue
        T = t[:n * M].reshape(-1, M)[:, -1]
        res = K.run(T, np.r_[C[0], C[:-1]], H, L, C, np.ones(n), np.zeros(n, int), params=dict(e_max=1.01, atr_k=None, min_w=float(mw), max_bars=mb))
        comp = {e["imp_id"]: e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"}
        for im in res["impulses"]:
            e = comp.get(im["imp_id"])
            if e is None or not im["W"] or e["bar"] < 60 or e["bar"] >= n - 2:
                continue
            k, d, A = e["bar"], im["dir"], im["A"]
            if mode == "cont":
                cd, fill = -d, A - d * 1.0
            else:
                if d * (A - (L[k] if d == 1 else H[k])) < 1:
                    continue
                cd, fill = d, A
            cands.append((str(f), k, cd, float(fill), float(im["W"])))
    rng = np.random.default_rng(SEED)
    if len(cands) > MAX_T:
        cands = [cands[i] for i in np.sort(rng.choice(len(cands), MAX_T, replace=False))]
    real_R, real_E, rnd_R, rnd_E, ses = [], [], [], [], []
    cache = {}
    for f, k, cd, fill, W in cands:
        if f not in cache:
            cache.clear(); z = np.load(f); h, l, c = (z[q].astype(float) for q in ("h", "l", "c"))
            H, L, C = agg(h, l, c); o = np.r_[c[0], c[:-1]]
            cache[f] = (H, L, C, np.column_stack([c - o, h - o, l - o]))
        H, L, C, trip = cache[f]; n = len(C)
        r = evaluate(H, L, C, trip, k, fill, cd, W, "real", f"{f}|real")
        if r is None:
            continue
        offs = fill - C[k]
        pos = np.array([q for q in range(60, n - 2) if abs(q - k) >= 50])
        if len(pos) < N_RAND:
            continue
        rr, ee, okn = np.zeros(len(KEYS)), np.zeros(len(KEYS)), 0
        for q in rng.choice(pos, N_RAND, replace=False):
            x = evaluate(H, L, C, trip, int(q), float(C[q] + offs), cd, W, "rnd", f"{f}|rnd")
            if x is not None:
                rr += x[0]; ee += x[1]; okn += 1
        if okn == 0:
            continue
        real_R.append(r[0]); real_E.append(r[1]); rnd_R.append(rr / okn); rnd_E.append(ee / okn); ses.append(Path(f).stem)
    real_R, real_E, rnd_R, rnd_E = map(np.array, (real_R, real_E, rnd_R, rnd_E)); ses = np.array(ses)
    u = np.unique(ses); idx = {x: np.flatnonzero(ses == x) for x in u}; B = 1000
    def ci(v):
        bs = [v[np.concatenate([idx[x] for x in rng.choice(u, len(u))])].mean() for _ in range(B)]
        return [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))]
    cells = []
    for j, key in enumerate(KEYS):
        cal = rnd_R[:, j] - rnd_E[:, j]; exn = real_R[:, j] - real_E[:, j]; emp = real_R[:, j] - rnd_R[:, j]
        cells.append(dict(celda=key, n=len(real_R), R_real=float(real_R[:, j].mean()), R_azar=float(rnd_R[:, j].mean()),
                          calibracion_nulo=float(cal.mean()), calibracion_ic90=ci(cal),
                          exceso_con_nulo=float(exn.mean()), exceso_con_nulo_ic90=ci(exn),
                          exceso_empirico=float(emp.mean()), exceso_empirico_ic90=ci(emp)))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / f"control_{case}.json").write_text(json.dumps(dict(case=case, candidatos=len(cands), trades=len(real_R), celdas=cells), indent=1), encoding="utf-8")
    print(case, "trades", len(real_R), flush=True)
    for c in cells:
        print(f"  {c['celda']:9s} R {c['R_real']:+.3f} azar {c['R_azar']:+.3f} | calib {c['calibracion_nulo']:+.3f} {c['calibracion_ic90']} | "
              f"exc_nulo {c['exceso_con_nulo']:+.3f} | exc_emp {c['exceso_empirico']:+.3f} {c['exceso_empirico_ic90']}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--case", required=True); ap.add_argument("--bars", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); run(a.case, a.bars, a.out)
