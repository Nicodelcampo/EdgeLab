"""Impulsos amplios, rapidos y que atraviesan muchas zonas LUX-IMB (OG + VI) vivas. Target-free: solo geometria.

Definiciones (version 1, a revisar en el visor con Nico):
- Impulso = detector ESPEJO-IND (`edgelab/bridge/indicators/espejo_impulsos.py::detect`, sin cambios), modo velas
  de tiempo: movimiento neto >= `--atr-k`·ATR(14) cerrado en la vela anterior, dentro de `--max-bars` velas,
  eficiencia >= 0,3; el tramo va de A (origen) a B (extremo). `--det zigzag` usa un zigzag de `--rev` puntos.
- Amplitud = rango del tramo en puntos. Rapidez = cantidad de velas del tramo.
- Zona atravesada por un impulso up: zona creada (vela de cierre ic) dentro de la vida `--vida` (1000 velas) al
  cruzarla, con fondo >= precio de inicio y techo <= precio final, y que dentro del tramo, DESPUES de crearse,
  el precio estuvo en o debajo del fondo y luego en o encima del techo (la cruzo entera). Simetrico para down.
  La edad se mide en la vela donde se completa el cruce: (j - ic) <= vida. Las zonas que crea el propio impulso
  y no vuelve a cruzar no cuentan.
- Marcado: amplitud >= percentil `--p` de todos los tramos, velas <= percentil (100-p) de los tramos, y
  zonas atravesadas >= percentil `--p` de los tramos. Los umbrales se publican en el JSON.

Uso: python tools/luximb_parity/luximb_impulsos.py <bundle.json> <out.json> [--rev 30] [--vida 1000] [--p 80]
"""
from __future__ import annotations

import argparse
import json

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from edgelab.bridge.indicators import espejo_impulsos as EI  # noqa: E402


def zigzag(h, l, rev):
    piv = []                       # (indice, precio, tipo 'H'/'L')
    d, ei, ep = 0, 0, None
    hi_i, lo_i = 0, 0
    for i in range(len(h)):
        if d == 0:
            if h[i] > h[hi_i]: hi_i = i
            if l[i] < l[lo_i]: lo_i = i
            if h[hi_i] - l[lo_i] >= rev:
                if hi_i > lo_i: piv.append((lo_i, l[lo_i], "L")); d, ei = 1, hi_i
                else: piv.append((hi_i, h[hi_i], "H")); d, ei = -1, lo_i
        elif d == 1:
            if h[i] >= h[ei]: ei = i
            elif h[ei] - l[i] >= rev:
                piv.append((ei, h[ei], "H")); d, ei = -1, i
        else:
            if l[i] <= l[ei]: ei = i
            elif h[i] - l[ei] >= rev:
                piv.append((ei, l[ei], "L")); d, ei = 1, i
    return piv


def crossed(a, b, up, h, l, zi, ztop, zbot, vida):
    """Cantidad de zonas vivas atravesadas enteras en el tramo a..b (indices de vela)."""
    p0, p1 = (l[a], h[b]) if up else (h[a], l[b])
    lo, hi = min(p0, p1), max(p0, p1)
    sel = np.flatnonzero((zi < b) & (zi >= a - vida) & (zbot >= lo) & (ztop <= hi))
    ids = []
    for k in sel:
        ic = zi[k]
        s = max(a, ic + 1)
        if s > b:
            continue
        if up:
            near = np.flatnonzero(l[s:b + 1] <= zbot[k])
            if not len(near): continue
            j0 = s + near[0]
            far = np.flatnonzero(h[j0:b + 1] >= ztop[k])
        else:
            near = np.flatnonzero(h[s:b + 1] >= ztop[k])
            if not len(near): continue
            j0 = s + near[0]
            far = np.flatnonzero(l[j0:b + 1] <= zbot[k])
        if not len(far): continue
        j = j0 + far[0]
        if j - ic <= vida:
            ids.append(int(k))
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("out")
    ap.add_argument("--rev", type=float, default=30.0)
    ap.add_argument("--vida", type=int, default=1000)
    ap.add_argument("--p", type=float, default=80.0)
    ap.add_argument("--det", default="espejo", choices=("espejo", "zigzag"))
    ap.add_argument("--atr-k", type=float, default=3.0)
    ap.add_argument("--max-bars", type=int, default=20)
    a = ap.parse_args()
    B = json.load(open(a.bundle, encoding="utf-8"))
    cd = B["bar_series"]["time_1m"]["candles"]
    t = np.array([c["time"] for c in cd]); h = np.array([c["high"] for c in cd]); l = np.array([c["low"] for c in cd])
    idx = {int(x): i for i, x in enumerate(t)}
    Z = B["runs"][0]["zones"]
    zi = np.array([idx[z["available_ts"] - 60] for z in Z])          # vela que crea la zona (marca = apertura)
    ztop = np.array([z["top"] for z in Z]); zbot = np.array([z["bottom"] for z in Z])
    if a.det == "espejo":
        tk = B["meta"]["tick_size"]
        o_ = np.array([c["open"] for c in cd]); c_ = np.array([c["close"] for c in cd]); v_ = np.array([c["volume"] for c in cd])
        H, L, C = np.round(h / tk), np.round(l / tk), np.round(c_ / tk)
        p = EI.params_of(dict(max_bars=a.max_bars, atr_k=a.atr_k))
        thr = a.atr_k * EI.atr_prev(H, L, C, p["atr_n"])
        imps = EI.detect(t.astype(float), H, L, C, v_, thr, p)
        pares = [(im["i0"], im["a"] * tk, im["iext"], im["ext"] * tk, im["d"] == 1) for im in imps]
    else:
        piv = zigzag(h, l, a.rev)
        pares = [(ia, pa, ib, pb, ka == "L") for (ia, pa, ka), (ib, pb, kb) in zip(piv[:-1], piv[1:])]
    legs = []
    for ia, pa, ib, pb, up in pares:
        ids = crossed(ia, ib, up, h, l, zi, ztop, zbot, a.vida)
        legs.append(dict(i0=ia, i1=ib, t0=int(t[ia]), t1=int(t[ib]), p0=float(pa), p1=float(pb), dir="up" if up else "down",
                         rango=round(abs(pb - pa), 2), velas=ib - ia, zonas=len(ids), zona_ids=[Z[k]["id"] for k in ids]))
    R = np.array([g["rango"] for g in legs]); V = np.array([g["velas"] for g in legs]); N = np.array([g["zonas"] for g in legs])
    u = dict(rango_min=float(np.percentile(R, a.p)), velas_max=float(np.percentile(V, 100 - a.p)), zonas_min=float(np.percentile(N, a.p)))
    u["zonas_min"] = max(u["zonas_min"], 1.0)
    for g in legs:
        g["marcado"] = bool(g["rango"] >= u["rango_min"] and g["velas"] <= u["velas_max"] and g["zonas"] >= u["zonas_min"])
    marc = [g for g in legs if g["marcado"]]
    res = dict(spec="LUXIMB-IMPULSOS-v1", bundle=B["meta"]["id"], params=dict(det=a.det, atr_k=a.atr_k, max_bars=a.max_bars, rev_pts=a.rev, vida_velas=a.vida, percentil=a.p),
               tramos=len(legs), umbrales=u, marcados=len(marc),
               resumen=dict(rango_mediana=float(np.median(R)), velas_mediana=float(np.median(V)), zonas_mediana=float(np.median(N)),
                            zonas_p90=float(np.percentile(N, 90)), zonas_max=int(N.max())),
               impulsos=marc, todos=[{k: g[k] for k in ("i0", "i1", "t0", "t1", "p0", "p1", "dir", "rango", "velas", "zonas", "marcado")} for g in legs])
    json.dump(res, open(a.out, "w", encoding="utf-8"), separators=(",", ":"))
    print(json.dumps({k: v for k, v in res.items() if k not in ("impulsos", "todos")}, indent=1))


if __name__ == "__main__":
    main()
