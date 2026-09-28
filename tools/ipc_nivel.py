#!/usr/bin/env python3
r"""IPC-NIVEL (Nico, 28/09): el precio se dio vuelta ≥ 2 veces en el mismo nivel, con mucho recorrido entre vueltas.

Target-free: sólo geometría, sin resultados. Diseño: docs/research/DISENO_IPC_ABANICO_DE_MECANISMOS_20260927.md §IPC-NIVEL.

    .venv\Scripts\python tools\ipc_nivel.py fit                          # congela parámetros con los 10 ejemplos de Nico
    .venv\Scripts\python tools\ipc_nivel.py detect --asset MES_03-26_202602_25T_HFT   # tanda ✓/✗ para el visor

Detector:
- Vueltas = pivotes de un zigzag sobre máximos/mínimos de 25t con reversión mínima R ticks (la «salida grande»).
- Un nivel arranca en una vuelta; suma visitas del mismo tipo a ≤ tol ticks del primer pico (la 3.ª y siguientes a
  ≤ 1,5 · tol, «aunque sea un poco menos evidente»). Una visita a menos de `sep` velas de la anterior es la misma visita
  (picos pegados: se agrupan, no suman). Un pivote que pasa el nivel por más de la tolerancia lo rompe y lo cierra;
  uno que se queda corto no lo rompe.
- Zona = ≥ 2 visitas (IPC-N2); se marca `n3` si tiene ≥ 3 (IPC-N3, candidato principal).
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
VIEW = REPO / "viewer" / "nt8_bridge"
TRAIN = "MES_03-26_202603_25T_HFT"
MAX_GAP = 200          # velas entre visitas: los ejemplos de Nico llegan a 147 (28/09); fijo, no se ajusta
GRID = dict(R=(12, 16, 20, 24, 28, 32, 40, 48), tol=(2, 3, 4, 6, 8), sep=(0, 15, 30, 60))


def load(asset):
    b = json.loads((VIEW / "bundles" / f"{asset}.json").read_text(encoding="utf-8"))
    tick = float(b["meta"]["tick_size"]); c = b["bar_series"]["tick_25"]["candles"]
    t = np.array([x["time"] for x in c], float)
    h = np.array([x["high"] for x in c]) / tick; l = np.array([x["low"] for x in c]) / tick
    return t, np.round(h), np.round(l), tick


def zigzag(h, l, t, R):
    """Pivotes (idx, kind, precio_ticks). Se reinicia en huecos > 30 min (frontera de sesión)."""
    piv = []; n = len(h); d = 0; ei = 0; ext = 0.0
    for j in range(n):
        if j and t[j] - t[j - 1] > 1800:
            d = 0
        if d == 0:
            d = 1; ei = j; ext = h[j]
            continue
        if d == 1:
            if h[j] >= ext:
                ext = h[j]; ei = j
            elif ext - l[j] >= R:
                piv.append((ei, "H", ext)); d = -1; ext = l[j]; ei = j
        else:
            if l[j] <= ext:
                ext = l[j]; ei = j
            elif h[j] - ext >= R:
                piv.append((ei, "L", ext)); d = 1; ext = h[j]; ei = j
    return piv


def levels(piv, tol, sep, t=None):
    out = []
    for kind in ("H", "L"):
        P = [p for p in piv if p[1] == kind]
        s = 1 if kind == "H" else -1
        used = set()
        for a in range(len(P)):
            if a in used:
                continue
            lvl = P[a][2]; visits = [[P[a]]]
            for b in range(a + 1, len(P)):
                q = P[b]; tl = tol if len(visits) < 2 else 1.5 * tol
                if q[0] - visits[-1][-1][0] > MAX_GAP or (t is not None and np.any(np.diff(t[visits[-1][-1][0]:q[0] + 1]) > 1800)):
                    break                                   # demasiado lejos o cruza la frontera de sesión: el nivel se cierra
                over = s * (q[2] - lvl)
                if over > tl:
                    break                                   # pasó el nivel: lo rompe
                if over < -tl:
                    continue                                # se quedó corto: no suma ni rompe
                if q[0] - visits[-1][-1][0] < sep:
                    visits[-1].append(q)                     # pico pegado: misma visita
                else:
                    visits.append([q])
                used.add(b)
            if len(visits) >= 2:
                pk = [p for v in visits for p in v]
                out.append(dict(kind=kind, visitas=len(visits), n3=len(visits) >= 3, picos=pk,
                                i0=pk[0][0], i1=pk[-1][0], lo=min(p[2] for p in pk), hi=max(p[2] for p in pk)))
    return out


def score(zones, lab, t):
    rev = lab.get("reviewed") or []
    win = [(r["t0"], r["t1"]) for r in rev]
    inwin = [z for z in zones if any(a <= t[z["i0"]] <= b for a, b in win)]
    G = lab["zigzags"]
    def match(z, g):
        gi = [p["i"] for p in g]; gp = [p["price"] for p in g]
        return (z["kind"] == g[0]["kind"] and min(z["i1"], max(gi)) - max(z["i0"], min(gi)) > 0)
    cov = np.mean([any(match(z, g) for z in inwin) for g in G]) if G else 0.0
    prec = np.mean([any(match(z, g) for g in G) for z in inwin]) if inwin else 0.0
    f1 = 2 * cov * prec / (cov + prec) if cov + prec else 0.0
    return dict(cobertura=float(cov), precision=float(prec), f1=float(f1), zonas_en_ventana=len(inwin))


def fit():
    t, h, l, tick = load(TRAIN)
    lab = json.loads((VIEW / "labels" / f"{TRAIN}.json").read_text(encoding="utf-8"))
    res = []
    for R, tol, sep in itertools.product(*GRID.values()):
        z = levels(zigzag(h, l, t, R), tol, sep, t)
        res.append(dict(R=R, tol=tol, sep=sep, **score(z, lab, t)))
    res.sort(key=lambda r: (-r["f1"], -r["cobertura"], r["R"]))
    out = dict(entrenado_con=TRAIN, grilla=GRID, elegido=res[0], top10=res[:10],
               nota="ajuste target-free contra los 10 grupos de Nico; la sesión revisada define la ventana de precisión")
    p = REPO / "docs" / "research" / "IPC_NIVEL_PARAMETROS_CONGELADOS_20260928.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(res[:10], indent=1))


def detect(asset):
    fr = json.loads((REPO / "docs" / "research" / "IPC_NIVEL_PARAMETROS_CONGELADOS_20260928.json").read_text(encoding="utf-8"))["elegido"]
    t, h, l, tick = load(asset)
    Z = levels(zigzag(h, l, t, fr["R"]), fr["tol"], fr["sep"], t)
    zonas = [dict(kind=z["kind"], i0=int(z["i0"]), i1=int(z["i1"]), t0=float(t[z["i0"]]), t1=float(t[z["i1"]]),
                  p0=float(z["lo"] * tick), p1=float(z["hi"] * tick), toques=int(z["visitas"]), n3=bool(z["n3"]),
                  picos=[[int(p[0]), float(t[p[0]]), float(p[2] * tick)] for p in z["picos"]]) for z in Z]
    dias = max(1.0, (t[-1] - t[0]) / 86400 * 5 / 7)
    d = dict(schema="EDGELAB_PEAKS_DET_V3_IPC_NIVEL", asset=asset, variante="IPC-NIVEL", parametros=fr, zonas=zonas,
             zonas_por_dia=round(len(zonas) / dias, 1))
    (VIEW / "bundles" / "peaks_det").mkdir(exist_ok=True)
    (VIEW / "bundles" / "peaks_det" / f"{asset}.json").write_text(json.dumps(d), encoding="utf-8")
    print(asset, "zonas", len(zonas), "N3", sum(z["n3"] for z in zonas), "por día", d["zonas_por_dia"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("step", choices=["fit", "detect"]); ap.add_argument("--asset")
    a = ap.parse_args()
    fit() if a.step == "fit" else detect(a.asset)
