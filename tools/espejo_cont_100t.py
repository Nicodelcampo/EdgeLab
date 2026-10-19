#!/usr/bin/env python3
r"""ESPEJO-CONT-100T-FILTROS — pedido de Nico 28/09 (corrida en Kaggle, datos Lucid).
Manifiesto: docs/research/MANIFIESTO_ESPEJO_CONT_100T_FILTROS_20260928.md

Entrada al completar el espejo (toque de A) a favor de la vuelta; velas 100t (4 × 25t por sesión); los 5 niveles de
permisividad del visor; grilla TP {0,25; 0,5; 1; 1,5; 2}×W × SL {0,25; 0,5; 1}×W (SL primero, cierre al horizonte de
150 velas o fin de sesión); exceso por trade = R − esperanza nula del mismo pago (simulate_null, 300 trayectorias,
ternas 25t estrictamente anteriores a la vela de entrada).
Filtros (causales, con la vela ANTERIOR a la de entrada): S2v2 (vuelta simétrica, igual que el visor: el último S2v2
no nulo del impulso), zona «no lista», impulso ineficiente (I1 ∨ I2), VWAP de sesión y EMA 20/50/200 sobre cierres de
100t, cada uno «a favor» (el precio del lado de la dirección de la entrada) o «en contra».
Multiplicidad: máximo estadístico sobre TODAS las celdas (nivel × subconjunto × grilla) por instrumento, bootstrap por
sesión recentrado; se publica el landscape completo.

    python tools/espejo_cont_100t.py --inst NQ --nivel 3 --bars DIR --out DIR
    python tools/espejo_cont_100t.py --report --out DIR
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

LEVELS = {1: (28, 16), 2: (22, 18), 3: (17, 20), 4: (13, 25), 5: (9, 30)}      # PERM_CONFIGS del visor (min_w, max_bars)
TPS = (0.25, 0.5, 1.0, 1.5, 2.0); SLS = (0.25, 0.5, 1.0)
KEYS = [f"{tp}_{sl}" for tp in TPS for sl in SLS]
M, HZ, N_NULL, N_BOOT, SLIP, MIN_N, SEED = 4, 150, 300, 1000, 1.0, 30, 20260928
MAX_TRADES = 8000          # por instrumento y nivel: si hay más, sorteo con semilla fija ANTES de simular (no mira desenlaces)
SUBSETS = ["todos", "S2v2", "no_S2v2", "no_lista", "sin_no_lista", "inef", "eficiente",
           "vwap_favor", "vwap_contra", "ema20_favor", "ema20_contra", "ema50_favor", "ema50_contra", "ema200_favor", "ema200_contra"]


def agg(h, l, c, v, t):
    n = len(c) // M * M
    return (h[:n].reshape(-1, M).max(1), l[:n].reshape(-1, M).min(1), c[:n].reshape(-1, M)[:, -1],
            v[:n].reshape(-1, M).sum(1), t[:n].reshape(-1, M)[:, -1])


def ema(x, span):
    a = 2 / (span + 1); out = np.empty(len(x)); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def trade(H, L, C, k, fill, c, tp, sl, end):
    T = fill + c * tp; S = fill - c * sl
    for j in range(k + 1, end + 1):
        if (L[j] <= S) if c == 1 else (H[j] >= S):
            return S
        if (H[j] >= T) if c == 1 else (L[j] <= T):
            return T
    return C[end]


def run(inst, nivel, bars_dir, out_dir):
    mw, mb = LEVELS[nivel]
    files = sorted(Path(bars_dir).glob("*.npz"))
    cands, prev = [], None
    for f in files:
        z = np.load(f); s = f.stem
        h, l, c, v = (z[k].astype(float) for k in ("h", "l", "c", "v")); t = z["t"].astype(float)
        H, L, C, V, T = agg(h, l, c, v, t); n = len(C)
        if n < 60:
            prev = None; continue
        o = np.r_[c[0], c[:-1]]; trip = np.column_stack([c - o, h - o, l - o])
        vwap = np.cumsum(C * V) / np.maximum(np.cumsum(V), 1e-9)
        emas = {p: ema(C, p) for p in (20, 50, 200)}
        res = K.run(T, np.r_[C[0], C[:-1]], H, L, C, V, np.zeros(n, int), params=dict(e_max=1.01, atr_k=None, min_w=float(mw), max_bars=mb))
        s2 = {}
        for e in res["events"]:
            if e["kind"] in ("MIRROR_CANDIDATE", "MIRROR_PROGRESS") and e.get("S2v2") is not None:
                s2[e["imp_id"]] = bool(e["S2v2"])
        comp = {e["imp_id"]: e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"}
        for im in res["impulses"]:
            e = comp.get(im["imp_id"])
            if e is None:
                continue
            k = e["bar"]; d = im["dir"]; A = im["A"]; W = im["W"]; cd = -d
            if k < 2 or k >= n - 2 or not W:
                continue
            fill = A + cd * SLIP; end = min(k + HZ, n - 1)
            pool = trip[:k * M]
            if len(pool) < 50 and prev is not None:
                pool = np.vstack([prev[-(200 - len(pool)):], pool])
            if len(pool) < 50:
                continue
            ref = C[k - 1]                                   # filtros con la vela anterior a la de entrada (causal)
            feat0 = dict(S2v2=s2.get(im["imp_id"], False), no_lista=im["no_lista_lo"] is not None, inef=bool(im["ineficiente"]),
                        vwap=bool(cd * (ref - vwap[k - 1]) > 0), **{f"ema{p}": bool(cd * (ref - emas[p][k - 1]) > 0) for p in emas})
            cands.append((s, f, k, cd, float(fill), int(end), float(W), feat0, len(pool)))
        prev = trip
    total = len(cands)
    if total > MAX_TRADES:
        pick = np.sort(np.random.default_rng(SEED + nivel).choice(total, MAX_TRADES, replace=False)); cands = [cands[i] for i in pick]
    rows, cache = [], {}
    for s, f, k, cd, fill, end, W, feat, _ in cands:
        if f not in cache:
            cache.clear(); z = np.load(f)
            h, l, c, v = (z[q].astype(float) for q in ("h", "l", "c", "v")); t = z["t"].astype(float)
            H, L, C, _, _ = agg(h, l, c, v, t); o = np.r_[c[0], c[:-1]]
            cache[f] = (H, L, C, np.column_stack([c - o, h - o, l - o]))
            fi = files.index(f)
            if fi > 0:
                zp = np.load(files[fi - 1]); hp, lp, cp = (zp[q].astype(float) for q in ("h", "l", "c")); op = np.r_[cp[0], cp[:-1]]
                cache["prev"] = np.column_stack([cp - op, hp - op, lp - op])
            else:
                cache["prev"] = None
        H, L, C, trip = cache[f]; pool = trip[:k * M]
        if len(pool) < 50 and cache["prev"] is not None:
            pool = np.vstack([cache["prev"][-(200 - len(pool)):], pool])
        exc = []
        for tp in TPS:
            for sl in SLS:
                R = cd * (trade(H, L, C, k, fill, cd, tp * W, sl * W, end) - fill) / W
                seed = int(hashlib.sha256(f"{inst}|{nivel}|{s}|{k}|{tp}|{sl}".encode()).hexdigest()[:8], 16)
                # nulo desde el CIERRE de la vela de entrada (ver espejo_cont_tpsl.py, fix 28/09)
                p0 = simulate_null(C[k], fill + cd * tp * W, fill - cd * sl * W, cd, pool, end - k, n=N_NULL, seed=seed, bars_per_step=M)
                E0 = p0["completa"] * tp - (p0["falla"] + p0["ambigua"]) * sl + p0["censurada"] * cd * (C[k] - fill) / W
                exc.append((float(R), float(R - E0)))
        rows.append(dict(session=s, W=float(W), **feat, R=[x[0] for x in exc], exc=[x[1] for x in exc]))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / f"trades_{inst}_N{nivel}.json").write_text(json.dumps(rows), encoding="utf-8")
    (Path(out_dir) / f"meta_{inst}_N{nivel}.json").write_text(json.dumps(dict(candidatos=total, simulados=len(rows))), encoding="utf-8")
    print(inst, "nivel", nivel, "candidatos", total, "simulados", len(rows), flush=True)


def masks(X):
    g = lambda k: np.array([r[k] for r in X], bool)
    s2, nl, ine, vw = g("S2v2"), g("no_lista"), g("inef"), g("vwap")
    e20, e50, e200 = g("ema20"), g("ema50"), g("ema200")
    return np.vstack([np.ones(len(X), bool), s2, ~s2, nl, ~nl, ine, ~ine, vw, ~vw, e20, ~e20, e50, ~e50, e200, ~e200])


def report(out_dir):
    out_dir = Path(out_dir); rep = {}
    for inst in sorted({p.name.split("_")[1] for p in out_dir.glob("trades_*_N*.json")}):
        blocks = []                                          # (nivel, subset, E (n×15), R, sesiones)
        for p in sorted(out_dir.glob(f"trades_{inst}_N*.json")):
            X = json.loads(p.read_text(encoding="utf-8")); nivel = int(p.stem.rsplit("_N", 1)[1])
            if not X:
                continue
            E = np.array([r["exc"] for r in X]); Rr = np.array([r["R"] for r in X]); ses = np.array([r["session"] for r in X])
            for si, mk in enumerate(masks(X)):
                blocks.append((nivel, SUBSETS[si], E[mk], Rr[mk], ses[mk]))
        u = np.unique(np.concatenate([b[4] for b in blocks]))
        idx = {x: i for i, x in enumerate(u)}; rng = np.random.default_rng(SEED)
        W = rng.multinomial(len(u), np.ones(len(u)) / len(u), size=N_BOOT).astype(float)          # pesos por sesión
        cells, tobs_all, tnull_all = [], [], []
        for nivel, sub, E, Rr, ses in blocks:
            n = len(E)
            if n < MIN_N:
                cells += [dict(nivel=nivel, subconjunto=sub, celda=k, n=n, sin_potencia=True) for k in KEYS]; continue
            S = np.zeros((len(u), E.shape[1])); N = np.zeros(len(u))
            si = np.array([idx[x] for x in ses]); np.add.at(S, si, E); np.add.at(N, si, 1)
            obs = E.mean(0); bm = (W @ S) / np.maximum(W @ N, 1e-9)[:, None]
            se = bm.std(0); t = obs / np.where(se > 0, se, np.nan)
            tobs_all.append(np.abs(t)); tnull_all.append(np.abs((bm - obs) / np.where(se > 0, se, np.nan)))
            for j, key in enumerate(KEYS):
                cells.append(dict(nivel=nivel, subconjunto=sub, celda=key, n=n, R_bruto_W=float(Rr[:, j].mean()), exceso_W=float(obs[j]),
                                  ic90=[float(np.quantile(bm[:, j], .05)), float(np.quantile(bm[:, j], .95))], t=float(t[j]),
                                  p_bilateral=float(np.mean(np.abs(bm[:, j] - obs[j]) >= abs(obs[j]))) if se[j] > 0 else 1.0))
        tobs = np.concatenate(tobs_all); tnull = np.nanmax(np.hstack(tnull_all), axis=1)
        p_global = float(np.mean(tnull >= np.nanmax(tobs)))
        crit = float(np.nanquantile(tnull, 0.95))
        for c in cells:
            c["sobrevive_max_t"] = bool(c.get("t") is not None and abs(c["t"]) >= crit)
        ok = [c for c in cells if "exceso_W" in c]
        rep[inst] = dict(celdas_probadas=len(ok), p_global=p_global, t_critico_95=crit,
                         sobreviven=[f"N{c['nivel']} {c['subconjunto']} {c['celda']} exc {c['exceso_W']:+.3f}" for c in ok if c["sobrevive_max_t"]],
                         top10=sorted(ok, key=lambda c: -c["exceso_W"])[:10], celdas=cells)
        print(inst, "celdas", len(ok), "p_global", p_global, "t crítico", round(crit, 2), "sobreviven", rep[inst]["sobreviven"][:10], flush=True)
    (out_dir / "reporte_100t_filtros.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--inst"); ap.add_argument("--nivel", type=int); ap.add_argument("--bars")
    ap.add_argument("--out", required=True); ap.add_argument("--report", action="store_true"); a = ap.parse_args()
    report(a.out) if a.report else run(a.inst, a.nivel, a.bars, a.out)
