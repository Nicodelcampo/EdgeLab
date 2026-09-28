#!/usr/bin/env python3
r"""ESPEJO-REV-100T — pedido de Nico 28/09 (Kaggle, datos Lucid). Manifiesto: docs/research/MANIFIESTO_ESPEJO_REV_100T_20260928.md

Después de completar el espejo (toque de A), ¿el precio se da vuelta hacia B?
A) CRUCE: evento = primer cierre del lado de B tras la completación (el precio «empieza a cruzar» el rango de vuelta).
   O = cuánto se alejó más allá de A antes (en W). Resultado para x ∈ {0,25; 0,5; 0,75; 1}: llega a A + x·W hacia B
   antes de un extremo nuevo más allá de A (1 tick más allá del extremo previo); horizonte 150 velas o fin de sesión.
   Nulo simulate_null desde el cierre del evento con esas barreras (ternas 25t estrictamente anteriores).
B) TP/SL de reversión: límite en A a favor de B (se llena sólo si la vela de completación pasó A ≥ 1 tick); grilla
   TP {0,25..2}×W × SL {0,25; 0,5; 1}×W; SL primero; nulo desde el cierre de la vela de entrada.
Configuraciones: GC W ≥ 100 t / 30 velas (la de Nico; excluye feb-2026, el mes que miró); ES/NQ/YM niveles 3–5 del
visor. Filtros: todos, y «no lista» + ineficiente. Multiplicidad: máximo estadístico por instrumento sobre todas las celdas.
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

M, HZ, N_NULL, N_BOOT, MIN_N, SEED, MAX_EV = 4, 150, 300, 1000, 30, 20260928, 8000
XS = (0.25, 0.5, 0.75, 1.0)
TPS = (0.25, 0.5, 1.0, 1.5, 2.0); SLS = (0.25, 0.5, 1.0)
KEYS = [f"{tp}_{sl}" for tp in TPS for sl in SLS]
CONFIGS = {"GC": {"W100": (100, 30)}, "ES": {"N3": (17, 20), "N4": (13, 25), "N5": (9, 30)},
           "NQ": {"N3": (17, 20), "N4": (13, 25), "N5": (9, 30)}, "YM": {"N3": (17, 20), "N4": (13, 25), "N5": (9, 30)}}
EXCLUDE = {"GC": ("202602",)}


def agg(h, l, c, v, t):
    n = len(c) // M * M
    return (h[:n].reshape(-1, M).max(1), l[:n].reshape(-1, M).min(1), c[:n].reshape(-1, M)[:, -1],
            v[:n].reshape(-1, M).sum(1), t[:n].reshape(-1, M)[:, -1])


def race(H, L, j, tgt, fail, s, end):
    for q in range(j + 1, end + 1):
        ht = (H[q] >= tgt) if s == 1 else (L[q] <= tgt)
        hf = (L[q] <= fail) if s == 1 else (H[q] >= fail)
        if ht and hf:
            return "ambigua"
        if ht:
            return "llega"
        if hf:
            return "falla"
    return "censurada"


def trade(H, L, C, k, fill, c, tp, sl, end):
    T = fill + c * tp; S = fill - c * sl
    for j in range(k + 1, end + 1):
        if (L[j] <= S) if c == 1 else (H[j] >= S):
            return S
        if (H[j] >= T) if c == 1 else (L[j] <= T):
            return T
    return C[end]


def pool_of(trip, k, prev):
    p = trip[:k * M]
    if len(p) < 50 and prev is not None:
        p = np.vstack([prev[-(200 - len(p)):], p])
    return p if len(p) >= 50 else None


def run(inst, cfg, bars_dir, out_dir):
    mw, mb = CONFIGS[inst][cfg]
    files = [f for f in sorted(Path(bars_dir).glob("*.npz")) if not f.stem.startswith(EXCLUDE.get(inst, ("x",)))]
    evA, evB, prev = [], [], None
    for f in files:
        z = np.load(f); s = f.stem
        h, l, c, v = (z[k].astype(float) for k in ("h", "l", "c", "v")); t = z["t"].astype(float)
        H, L, C, V, T = agg(h, l, c, v, t); n = len(C)
        if n < 60:
            prev = None; continue
        o = np.r_[c[0], c[:-1]]; trip = np.column_stack([c - o, h - o, l - o])
        res = K.run(T, np.r_[C[0], C[:-1]], H, L, C, V, np.zeros(n, int), params=dict(e_max=1.01, atr_k=None, min_w=float(mw), max_bars=mb))
        comp = {e["imp_id"]: e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"}
        for im in res["impulses"]:
            e = comp.get(im["imp_id"])
            if e is None or not im["W"]:
                continue
            k = e["bar"]; d = im["dir"]; A = im["A"]; W = im["W"]; s_b = d            # hacia B = dirección del impulso
            if k >= n - 2:
                continue
            filt = bool(im["no_lista_lo"] is not None and im["ineficiente"])
            # A) cruce
            E = A; j = None
            for q in range(k, n - 1):
                E = min(E, L[q]) if d == 1 else max(E, H[q])            # extremo más allá de A (del lado opuesto a B)
                if d * (C[q] - A) > 0:
                    j = q; break
            if j is not None:
                O = d * (A - E) / W
                end = min(j + HZ, n - 1); pool = pool_of(trip, j, prev)
                if pool is not None and end > j:
                    fail = E - d * 1
                    r = dict(session=s, W=float(W), filt=filt, O=float(O), res={}, p0={})
                    for x in XS:
                        tgt = A + d * x * W
                        seed = int(hashlib.sha256(f"A|{inst}|{cfg}|{s}|{j}|{x}".encode()).hexdigest()[:8], 16)
                        r["res"][str(x)] = race(H, L, j, tgt, fail, s_b, end)
                        r["p0"][str(x)] = simulate_null(C[j], tgt, fail, s_b, pool, end - j, n=N_NULL, seed=seed, bars_per_step=M)["completa"]
                    evA.append(r)
            # B) TP/SL de reversión: límite en A, se llena si la vela de completación pasó A por ≥ 1 tick
            passed = (d * (A - (L[k] if d == 1 else H[k]))) >= 1
            if passed:
                end = min(k + HZ, n - 1); pool = pool_of(trip, k, prev)
                if pool is not None and end > k:
                    exc, R = [], []
                    for tp in TPS:
                        for sl in SLS:
                            px = trade(H, L, C, k, A, s_b, tp * W, sl * W, end); Rr = s_b * (px - A) / W
                            seed = int(hashlib.sha256(f"B|{inst}|{cfg}|{s}|{k}|{tp}|{sl}".encode()).hexdigest()[:8], 16)
                            p0 = simulate_null(C[k], A + s_b * tp * W, A - s_b * sl * W, s_b, pool, end - k, n=N_NULL, seed=seed, bars_per_step=M)
                            E0 = p0["completa"] * tp - (p0["falla"] + p0["ambigua"]) * sl + p0["censurada"] * s_b * (C[k] - A) / W
                            R.append(float(Rr)); exc.append(float(Rr - E0))
                    evB.append(dict(session=s, W=float(W), filt=filt, R=R, exc=exc))
        prev = trip
        if len(evA) > MAX_EV and len(evB) > MAX_EV:
            break                                      # tope de cómputo (orden cronológico: se declara en el reporte)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / f"rev_{inst}_{cfg}.json").write_text(json.dumps(dict(A=evA, B=evB, sesiones=len(files))), encoding="utf-8")
    print(inst, cfg, "cruces", len(evA), "trades", len(evB), flush=True)


def _boot(vals_by_cell, ses_by_cell, u, W):
    idx = {x: i for i, x in enumerate(u)}; out = []
    for vals, ses in zip(vals_by_cell, ses_by_cell):
        S = np.zeros(len(u)); N = np.zeros(len(u)); si = np.array([idx[x] for x in ses])
        np.add.at(S, si, vals); np.add.at(N, si, 1)
        out.append((W @ S) / np.maximum(W @ N, 1e-9))
    return out


def report(out_dir):
    out_dir = Path(out_dir); rep = {}
    for inst in sorted({p.stem.split("_")[1] for p in out_dir.glob("rev_*.json")}):
        cells = []
        for p in sorted(out_dir.glob(f"rev_{inst}_*.json")):
            cfg = p.stem.split("_")[2]; D = json.loads(p.read_text(encoding="utf-8"))
            for fname, fsel in (("todos", lambda r: True), ("no_lista+inef", lambda r: r["filt"])):
                A = [r for r in D["A"] if fsel(r)]
                if A:
                    Os = np.array([r["O"] for r in A]); q = np.quantile(Os, [1 / 3, 2 / 3]) if len(A) >= 3 else [0, 0]
                    ter = np.where(Os <= q[0], "O_bajo", np.where(Os > q[1], "O_alto", "O_medio"))
                    for x in XS:
                        vals = np.array([(r["res"][str(x)] == "llega") - r["p0"][str(x)] for r in A]); ses = np.array([r["session"] for r in A])
                        for tname in ("O_todos", "O_bajo", "O_medio", "O_alto"):
                            m = np.ones(len(A), bool) if tname == "O_todos" else ter == tname
                            cells.append(dict(parte="A_cruce", cfg=cfg, filtro=fname, x=x, overshoot=tname, n=int(m.sum()),
                                              llega=float(np.mean([A[i]["res"][str(x)] == "llega" for i in np.flatnonzero(m)])) if m.any() else None,
                                              _v=vals[m], _s=ses[m], corte_O=[float(v) for v in q]))
                B = [r for r in D["B"] if fsel(r)]
                if B:
                    E = np.array([r["exc"] for r in B]); Rr = np.array([r["R"] for r in B]); ses = np.array([r["session"] for r in B])
                    for j, key in enumerate(KEYS):
                        cells.append(dict(parte="B_tpsl", cfg=cfg, filtro=fname, celda=key, n=len(B), R_bruto_W=float(Rr[:, j].mean()), _v=E[:, j], _s=ses))
        ok = [c for c in cells if c["n"] >= MIN_N]
        if not ok:
            continue
        u = np.unique(np.concatenate([c["_s"] for c in ok])); rng = np.random.default_rng(SEED)
        Wb = rng.multinomial(len(u), np.ones(len(u)) / len(u), size=N_BOOT).astype(float)
        bms = _boot([c["_v"] for c in ok], [c["_s"] for c in ok], u, Wb)
        tnull = np.zeros(N_BOOT)
        for c, bm in zip(ok, bms):
            obs = float(np.mean(c["_v"])); se = float(bm.std())
            c.update(exceso=obs, ic90=[float(np.quantile(bm, .05)), float(np.quantile(bm, .95))], t=obs / se if se > 0 else 0.0)
            if se > 0:
                tnull = np.maximum(tnull, np.abs((bm - obs) / se))
        crit = float(np.quantile(tnull, .95))
        for c in cells:
            c.pop("_v", None); c.pop("_s", None)
            c["sobrevive_max_t"] = bool(c.get("t") is not None and abs(c["t"]) >= crit)
        rep[inst] = dict(t_critico_95=crit, celdas=cells,
                         sobreviven=[{k: v for k, v in c.items() if k in ("parte", "cfg", "filtro", "x", "overshoot", "celda", "n", "exceso", "R_bruto_W", "llega")}
                                     for c in cells if c["sobrevive_max_t"]])
        print(inst, "t crítico", round(crit, 2), "sobreviven", len(rep[inst]["sobreviven"]), flush=True)
    (out_dir / "reporte_rev_100t.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--inst"); ap.add_argument("--cfg"); ap.add_argument("--bars")
    ap.add_argument("--out", required=True); ap.add_argument("--report", action="store_true"); a = ap.parse_args()
    report(a.out) if a.report else run(a.inst, a.cfg, a.bars, a.out)
