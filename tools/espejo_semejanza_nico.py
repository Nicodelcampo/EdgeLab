#!/usr/bin/env python3
r"""Semejanza «a lo Nico» entre la ida A→B y la vuelta, validada contra sus órdenes por tandas de a tres (target-free).

Criterio de Nico (28/09): simetría ida/vuelta; si la ida tuvo un retroceso y la vuelta no, baja; si la vuelta espeja la
velocidad, sube; impulso fuerte contra vuelta escalonada, baja. Rasgos (ida = último tramo de la ida que la vuelta
espeja, invertido en el tiempo):
  f_vel   |log(duración vuelta / duración ida-espejo)|
  f_pb_n  |n.º retrocesos ≥ 10 % W en la vuelta − en la ida-espejo|
  f_pb_d  |profundidad máxima de retroceso (en W) vuelta − ida-espejo|
  f_eff   |eficiencia vuelta − eficiencia ida-espejo|
  f_dtw   DTW entre los dos caminos normalizados (fracción de W vs tiempo normalizado)
Menor = más parecido. Validación: comparaciones de a pares de cada tanda (1>2, 1>3, 2>3); logística sobre diferencias
de rasgos, con **dejar una tanda afuera**. Se reporta la precisión de cada rasgo solo y del modelo, y el azar (50 %).

    .venv\Scripts\python tools\espejo_semejanza_nico.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
NAME = "espejo_triads_ES_2026Q1_100t"
FEATS = ("f_vel", "f_pb_n", "f_pb_d", "f_eff", "f_dtw")


def _zig(y, thr):
    """Retrocesos (contra la dirección neta) de al menos `thr`: cantidad y profundidad máxima."""
    n = 0; depth = 0.0; ext = y[0]
    for v in y[1:]:
        if v > ext:
            ext = v
        else:
            dd = ext - v
            depth = max(depth, dd)
            if dd >= thr:
                n += 1; ext = v
    return n, depth


def _dtw(a, b):
    n, m = len(a), len(b)
    D = np.full((n + 1, m + 1), np.inf); D[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = abs(a[i - 1] - b[j - 1]) + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return D[n, m] / (n + m)


def features(it):
    c = np.array([x["close"] for x in it["candles"]], float)
    A, B, iA, iB, d = it["A"], it["B"], it["iA"], it["iB"], it["dir"]
    W = abs(B - A)
    ret = c[iB:]                                        # vuelta desde B hasta el corte
    f = min(abs(ret[-1] - B) / W, 1.0) if W > 0 else 0.0
    ida = c[iA:iB + 1]
    prog = d * (ida - A) / W                            # 0 → 1
    k = np.where(prog <= 1 - f)[0]
    m = iA + (int(k[-1]) if len(k) else 0)
    esp = c[m:iB + 1][::-1]                             # ida-espejo invertida: arranca en B
    y_esp = d * (B - esp) / W                           # 0 en B, crece hacia A (avance del espejo)
    y_ret = d * (B - ret) / W
    n1, d1 = _zig(y_esp, 0.1); n2, d2 = _zig(y_ret, 0.1)

    def eff(y):
        p = np.abs(np.diff(y)).sum()
        return abs(y[-1] - y[0]) / p if p > 0 else 1.0
    t_e = np.linspace(0, 1, len(y_esp)); t_r = np.linspace(0, 1, len(y_ret))
    grid = np.linspace(0, 1, 20)
    return dict(f_vel=abs(np.log(max(len(y_ret) - 1, 1) / max(len(y_esp) - 1, 1))), f_pb_n=abs(n2 - n1), f_pb_d=abs(d2 - d1),
                f_eff=abs(eff(y_ret) - eff(y_esp)), f_dtw=_dtw(np.interp(grid, t_e, y_esp), np.interp(grid, t_r, y_ret)))


def main():
    D = json.loads((REPO / "viewer" / "nt8_bridge" / "bundles" / f"{NAME}.json").read_text(encoding="utf-8"))
    L = json.loads((REPO / "viewer" / "nt8_bridge" / "labels" / f"{NAME}.json").read_text(encoding="utf-8"))["judgments"]
    F = {it["id"]: features(it) for it in D["items"]}
    pairs = []                                          # (tanda, mejor, peor)
    for k, j in L.items():
        r = j["ranked_items"]
        pairs += [(k, r[0], r[1]), (k, r[0], r[2]), (k, r[1], r[2])]
    X = np.array([[F[w][f] - F[b][f] for f in FEATS] for _, b, w in pairs])   # peor − mejor: > 0 si el rasgo ordena bien
    g = np.array([p[0] for p in pairs])
    out = {"pares": len(pairs), "tandas": len(L), "azar": 0.5, "por_rasgo": {}}
    for i, f in enumerate(FEATS):
        out["por_rasgo"][f] = float(np.mean(X[:, i] > 0) + 0.5 * np.mean(X[:, i] == 0))
    # logística sin intercepto (simétrica) sobre rasgos estandarizados, dejando una tanda afuera
    from sklearn.linear_model import LogisticRegression
    sd = X.std(axis=0); sd[sd == 0] = 1
    Z = X / sd
    Zs = np.vstack([Z, -Z]); ys = np.r_[np.ones(len(Z)), np.zeros(len(Z))]; gs = np.r_[g, g]
    hits = []
    for t in np.unique(g):
        tr = gs != t
        mdl = LogisticRegression(fit_intercept=False, C=1.0).fit(Zs[tr], ys[tr])
        hits += list((Z[g == t] @ mdl.coef_[0]) > 0)
    full = LogisticRegression(fit_intercept=False, C=1.0).fit(Zs, ys)
    out["modelo_dejar_una_tanda_afuera"] = float(np.mean(hits))
    out["pesos_modelo_completo"] = {f: float(w) for f, w in zip(FEATS, full.coef_[0])}
    d = REPO / "artifacts" / "espejo" / "triadas"; d.mkdir(parents=True, exist_ok=True)
    (d / f"semejanza_nico_{NAME}.json").write_text(json.dumps(dict(out, rasgos=F), indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
