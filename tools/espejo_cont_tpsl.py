#!/usr/bin/env python3
r"""ESPEJO-CONT-TPSL — OK de Nico 28/09. Manifiesto: docs/research/MANIFIESTO_ESPEJO_CONTINUACION_TPSL_20260928.md

Entrada al completar el espejo (toque de A) a favor de la vuelta: orden stop en A, llenado A + 1 tick en contra.
Grilla TP {0,25; 0,5; 1; 1,5; 2}×W × SL {0,25; 0,5; 1}×W; SL primero si la vela toca los dos; cierre al horizonte
(600 velas 25t / 150 velas 100t) o fin de sesión. Exceso por trade = R realizado − esperanza nula del mismo pago
(simulate_null, ternas 25t estrictamente anteriores a la vela de entrada). Control C-RUP (descriptivo): ruptura del
extremo de las 2×duración velas previas, sin espejo, misma sesión, misma W.
Multiplicidad: máximo estadístico de la grilla (bootstrap por sesión, recentrado) + BH q = 0,10 por celda.

    .venv\Scripts\python tools\espejo_cont_tpsl.py --config C1N5   # ES 25t nivel 5 (también C1N4, C2N5, C3N4, C3N5)
    .venv\Scripts\python tools\espejo_cont_tpsl.py --config C2     # ES 100t
    .venv\Scripts\python tools\espejo_cont_tpsl.py --config C3     # MNQ 25t (requiere velas en artifacts/tbzx/bars_MNQ)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402
from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402
from edgelab.research.espejo_nulo import simulate_null  # noqa: E402

OUT = REPO / "artifacts" / "espejo" / "cont_tpsl"
# Enmienda 1 (28/09, Nico: «es necesario que haya muchos más trades»; antes de mirar resultados): niveles 4 y 5 del
# slider de permisividad del visor (13 t/25 velas y 9 t/30 velas); el nivel 3 daba ~0,8 completados por sesión en ES 25t.
CONFIGS = {"C1N4": dict(inst="ES", mult=1, min_w=13.0, max_bars=25, hz=600),
           "C1N5": dict(inst="ES", mult=1, min_w=9.0, max_bars=30, hz=600),
           "C2N5": dict(inst="ES", mult=4, min_w=18.0, max_bars=30, hz=150),
           "C3N4": dict(inst="MNQ", mult=1, min_w=13.0, max_bars=25, hz=600),
           "C3N5": dict(inst="MNQ", mult=1, min_w=9.0, max_bars=30, hz=600)}
TPS = (0.25, 0.5, 1.0, 1.5, 2.0); SLS = (0.25, 0.5, 1.0)
N_NULL, N_BOOT, SEED, SLIP = 1000, 1000, 20260928, 1.0
MIN_N = 30                                   # trades mínimos por estrato para probar


def agg(h, l, c, m):
    n = len(c) // m * m
    return h[:n].reshape(-1, m).max(1), l[:n].reshape(-1, m).min(1), c[:n].reshape(-1, m)[:, -1]


def trade(H, L, C, k, fill, c, tp, sl, end):
    """R en unidades de la distancia (no de W): devuelve precio de salida y motivo."""
    T = fill + c * tp; S = fill - c * sl
    for j in range(k + 1, end + 1):
        hit_s = (L[j] <= S) if c == 1 else (H[j] >= S)
        hit_t = (H[j] >= T) if c == 1 else (L[j] <= T)
        if hit_s:
            return S, "sl"
        if hit_t:
            return T, "tp"
    return C[end], "cierre"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True, choices=list(CONFIGS)); a = ap.parse_args()
    cf = CONFIGS[a.config]; m = cf["mult"]
    OUT.mkdir(parents=True, exist_ok=True)
    lock = OUT / f"lock_{a.config}"                    # 28/09: una sola corrida por configuración (colas paralelas)
    if lock.exists():
        print(a.config, "ya corriendo o terminada (candado", lock.name + "): se saltea"); return
    lock.write_text(str(__import__("os").getpid()), encoding="utf-8")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    bd = T2.bars_dir(cf["inst"])
    ss = [s["trade_date"] for s in T2.canonical_sessions(cf["inst"]) if s["trade_date"] <= TB.EXP_END and (bd / f"{s['trade_date']}.npz").exists()]
    kp = dict(e_max=1.01, atr_k=None, min_w=cf["min_w"], max_bars=cf["max_bars"])
    rows, prev = [], None
    for si, s in enumerate(ss):
        z = np.load(bd / f"{s}.npz")
        h, l, c, v = (z[k].astype(float) for k in ("h", "l", "c", "v")); t = z["t"].astype(float)
        H, L, C = agg(h, l, c, m); n = len(C)
        if n < 50:
            continue
        T = t[:n * m].reshape(-1, m)[:, -1]; V = v[:n * m].reshape(-1, m).sum(1)
        o = np.r_[c[0], c[:-1]]; trip = np.column_stack([c - o, h - o, l - o])
        res = K.run(T, np.r_[C[0], C[:-1]], H, L, C, V, np.zeros(n, int), params=kp)
        comp = {e["imp_id"]: e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"}
        rup = {}
        for im in res["impulses"]:
            e = comp.get(im["imp_id"])
            if e is None or im["eff"] < 0.3:
                continue
            k = e["bar"]; d = im["dir"]; A = im["A"]; W = im["W"]; cdir = -d
            if k >= n - 2:
                continue
            fill = A + cdir * SLIP
            end = min(k + cf["hz"], n - 1)
            pool = trip[:k * m]
            if len(pool) < 50 and prev is not None:
                pool = np.vstack([prev[-(200 - len(pool)):], pool])
            if len(pool) < 50:
                continue
            dur = im["bar_B"] - im["bar_A"] + 1
            # control C-RUP: ruptura del extremo de las 2·dur velas previas en la dirección cdir, sin espejo cerca
            lb = 2 * dur
            if (lb, cdir) not in rup:
                import pandas as pd
                if cdir == 1:
                    prevx = pd.Series(H).rolling(lb).max().shift(1).to_numpy(); rup[(lb, cdir)] = np.flatnonzero(H > prevx)
                else:
                    prevx = pd.Series(L).rolling(lb).min().shift(1).to_numpy(); rup[(lb, cdir)] = np.flatnonzero(L < prevx)
            brk = rup[(lb, cdir)]
            brk = brk[(np.abs(brk - k) > 50) & (brk < n - 2)]
            kc = int(brk[np.argmin(np.abs(brk - k))]) if len(brk) else None
            rec = dict(session=s, estrato="TBZ" if im["eff"] >= 0.6 else "otros", W=float(W), bar=int(k), cells={}, ctrl={})
            for tp in TPS:
                for sl in SLS:
                    key = f"{tp}_{sl}"
                    px, why = trade(H, L, C, k, fill, cdir, tp * W, sl * W, end)
                    R = cdir * (px - fill) / W
                    seed = int(hashlib.sha256(f"{a.config}|{s}|{k}|{key}".encode()).hexdigest()[:8], 16)
                    # 28/09: el nulo arranca en el CIERRE de la vela de entrada (el toque de A es por mecha y la vela suele
                    # cerrar del lado de B); antes arrancaba en `fill` y sesgaba el exceso en contra. Censura: el cierre
                    # esperado de un paseo sin deriva es el punto de partida → aporta cdir·(C[k] − fill)/W.
                    p0 = simulate_null(C[k], fill + cdir * tp * W, fill - cdir * sl * W, cdir, pool, end - k, n=N_NULL, seed=seed, bars_per_step=m)
                    Ep = p0["completa"] * tp - (p0["falla"] + p0["ambigua"]) * sl + p0["censurada"] * cdir * (C[k] - fill) / W
                    rec["cells"][key] = dict(R=float(R), E0=float(Ep), exc=float(R - Ep), why=why)
                    if kc is not None:
                        fc = C[kc]; endc = min(kc + cf["hz"], n - 1)
                        pxc, _ = trade(H, L, C, kc, fc, cdir, tp * W, sl * W, endc)
                        poolc = trip[:kc * m]
                        if len(poolc) >= 50:
                            p0c = simulate_null(fc, fc + cdir * tp * W, fc - cdir * sl * W, cdir, poolc, endc - kc, n=N_NULL, seed=seed + 1, bars_per_step=m)
                            rec["ctrl"][key] = float(cdir * (pxc - fc) / W - (p0c["completa"] * tp - (p0c["falla"] + p0c["ambigua"]) * sl))
            rows.append(rec)
        prev = trip
        if si % 20 == 0:
            print(a.config, s, si + 1, "/", len(ss), "trades", len(rows), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"trades_{a.config}.json").write_text(json.dumps(rows), encoding="utf-8")
    rng = np.random.default_rng(SEED); cells = []
    for estr in ("TBZ", "otros"):
        X = [r for r in rows if r["estrato"] == estr]
        if len(X) < MIN_N:                               # sin potencia: se publica, no se prueba (bootstrap degenerado)
            cells.append(dict(config=a.config, estrato=estr, n=len(X), sin_potencia=True, p_bilateral=1.0))
            continue
        ses = np.array([r["session"] for r in X]); u = np.unique(ses); idx = {x: np.flatnonzero(ses == x) for x in u}
        keys = [f"{tp}_{sl}" for tp in TPS for sl in SLS]
        E = np.array([[r["cells"][k]["exc"] for k in keys] for r in X]); Rg = np.array([[r["cells"][k]["R"] for k in keys] for r in X])
        obs = E.mean(0); boots = np.empty((N_BOOT, len(keys)))
        for bi in range(N_BOOT):
            ii = np.concatenate([idx[x] for x in rng.choice(u, len(u))]); boots[bi] = E[ii].mean(0)
        se = boots.std(0); tobs = obs / np.where(se > 0, se, np.nan)
        tmax_null = np.nanmax(np.abs((boots - obs) / np.where(se > 0, se, np.nan)), axis=1)      # recentrado (White RC)
        p_global = float(np.mean(tmax_null >= np.nanmax(np.abs(tobs)))) if np.isfinite(tobs).any() else 1.0
        for j, key in enumerate(keys):
            ctrl = [r["ctrl"][key] for r in X if key in r["ctrl"]]
            p = float(np.mean(np.abs(boots[:, j] - obs[j]) >= abs(obs[j]))) if se[j] > 0 else 1.0   # bilateral, recentrado
            cells.append(dict(config=a.config, estrato=estr, tp=float(key.split("_")[0]), sl=float(key.split("_")[1]), n=len(X),
                              R_bruto_W=float(Rg[:, j].mean()), R_bruto_ticks=float((Rg[:, j] * np.array([r["W"] for r in X])).mean()),
                              E0_W=float(np.mean([r["cells"][key]["E0"] for r in X])), exceso_W=float(obs[j]),
                              ic90=[float(np.quantile(boots[:, j], .05)), float(np.quantile(boots[:, j], .95))], t=float(tobs[j]),
                              p_bilateral=p, exceso_control_W=float(np.mean(ctrl)) if ctrl else None, n_control=len(ctrl),
                              p_global_estrato=p_global))
    ps = np.array([c["p_bilateral"] for c in cells]); o = np.argsort(ps); mm = len(ps)
    ok = ps[o] <= 0.10 * np.arange(1, mm + 1) / mm; kmax = (np.max(np.flatnonzero(ok)) + 1) if ok.any() else 0
    surv = set(o[:kmax].tolist())
    for i, c in enumerate(cells):
        c["bh_q10"] = i in surv
    rep = dict(manifiesto="docs/research/MANIFIESTO_ESPEJO_CONTINUACION_TPSL_20260928.md", config=a.config, **cf, code_commit=head,
               tree_dirty=dirty, sesiones=len(ss), trades=len(rows), celdas=cells,
               sobreviven_bh=[f"{c['estrato']} tp={c['tp']} sl={c['sl']}" for c in cells if c["bh_q10"]],
               p_global={c["estrato"]: c.get("p_global_estrato") for c in cells})
    (OUT / f"reporte_{a.config}.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(config=a.config, trades=len(rows), p_global=rep["p_global"], sobreviven=rep["sobreviven_bh"]), ensure_ascii=False))
    for c in sorted([c for c in cells if "exceso_W" in c], key=lambda c: -c["exceso_W"])[:6]:
        print(c["estrato"], c["tp"], c["sl"], c["n"], "R", round(c["R_bruto_W"], 3), "E0", round(c["E0_W"], 3), "exc", round(c["exceso_W"], 3),
              [round(x, 3) for x in c["ic90"]], "ctrl", c["exceso_control_W"] and round(c["exceso_control_W"], 3))


if __name__ == "__main__":
    main()
