#!/usr/bin/env python3
r"""Detector de «picos consecutivos» (acumulaciones de liquidez) aprendido de las etiquetas de Nico. Versión 0.

    .venv\Scripts\python tools\peaks_learn.py --asset ES_03-26_202601_25T_HFT

- Lee `viewer/nt8_bridge/labels/<asset>.json` (rangos y grupos de picos) y las velas del bundle.
- Detector causal: en la vela j, mirando las últimas W velas, hay ≥ Nmin pivotes del mismo tipo (máximos o mínimos
  con w velas a cada lado, confirmados w velas después) dentro de una banda de τ ticks pegada al extremo de la ventana.
  La zona dura mientras la condición se sostiene y termina al romperse (el precio pasa la banda por más de τ).
- Ajuste: grilla de (W, τ, Nmin, w) y se elige la que mejor coincide (F1) con los rangos etiquetados, dentro de la
  ventana que Nico revisó (**supuesto declarado:** desde 30 min antes del primer rango hasta 10 min después del
  último, en las sesiones con etiquetas y sin «sesión revisada»; con sesiones revisadas se usan esas).
- Salida: `viewer/nt8_bridge/bundles/peaks_det/<asset>.json` con las zonas de TODO el bundle, para evaluarlas a ojo
  fuera de lo etiquetado. Sin resultados de trading.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from numba import njit

REPO = Path(__file__).resolve().parents[1]
VIEW = REPO / "viewer" / "nt8_bridge"
GRID = dict(W=(100, 150, 250), tau=(2, 4, 6), nmin=(4, 6, 8), w=(1, 2), gap=(0, 20, 60), dmin=(0, 30))


@njit(cache=True)
def detect(h, l, t, tick, W, tau, nmin, w, kind):
    """Zonas (i0, i1, piso, techo, toques). kind = 1 máximos, -1 mínimos. Causal: el pivote q se conoce en q + w."""
    n = len(h)
    x = h if kind == 1 else -l                      # trabajar siempre como «techo»
    piv = np.zeros(n, np.bool_)
    for q in range(w, n - w):
        ok = True
        for o in range(1, w + 1):
            if x[q] < x[q - o] or x[q] < x[q + o]:
                ok = False
                break
        piv[q] = ok
    out = np.zeros((n // 10 + 10, 5))
    m = 0
    active = False
    z0 = 0; top = 0.0; cnt = 0
    for j in range(W + w, n):
        if t[j] - t[j - 1] > 1800:                  # no cruzar sesiones
            active = False
        a = j - W
        hi = -1e18
        for q in range(a, j - w + 1):
            if piv[q] and x[q] > hi:
                hi = x[q]
        c = 0; first = -1
        for q in range(a, j - w + 1):
            if piv[q] and x[q] >= hi - tau * tick:
                c += 1
                if first < 0:
                    first = q
        broke = x[j] > hi + tau * tick
        cond = c >= nmin and not broke
        if cond and not active:
            active = True; z0 = first; top = hi; cnt = c
        elif cond and active:
            top = max(top, hi); cnt = max(cnt, c)
        elif active and not cond:
            out[m, 0] = z0; out[m, 1] = j; out[m, 2] = top - tau * tick; out[m, 3] = top; out[m, 4] = cnt
            m += 1
            active = False
    return out[:m]


def merge(Z, gap, dmin):
    """Une fragmentos del mismo tipo con bandas superpuestas y separados por ≤ gap velas; descarta zonas < dmin velas."""
    out = []
    for kind in ("H", "L"):
        zs = sorted((z for z in Z if z["kind"] == kind), key=lambda z: z["i0"])
        cur = None
        for z in zs:
            if cur and z["i0"] - cur["i1"] <= gap and z["p0"] <= cur["p1"] and z["p1"] >= cur["p0"]:
                cur.update(i1=max(cur["i1"], z["i1"]), t1=max(cur["t1"], z["t1"]), p0=min(cur["p0"], z["p0"]), p1=max(cur["p1"], z["p1"]),
                           toques=max(cur["toques"], z["toques"]))
            else:
                if cur:
                    out.append(cur)
                cur = dict(z)
        if cur:
            out.append(cur)
    return [z for z in out if z["i1"] - z["i0"] >= dmin]


def zones(cd, tick, W, tau, nmin, w):
    Z = []
    for kind in (1, -1):
        for r in detect(cd["h"], cd["l"], cd["t"], tick, W, tau, nmin, w, kind):
            i0, i1 = int(r[0]), int(r[1])
            p0, p1 = (r[2], r[3]) if kind == 1 else (-r[3], -r[2])
            Z.append(dict(kind="H" if kind == 1 else "L", i0=i0, i1=i1, t0=float(cd["t"][i0]), t1=float(cd["t"][i1]),
                          p0=float(p0), p1=float(p1), toques=int(r[4])))
    return Z


def overlap(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def iou(a0, a1, b0, b1):
    inter = overlap(a0, a1, b0, b1)
    return inter / max(max(a1, b1) - min(a0, b0), 1)


def score(Z, R, win):
    """F1 por eventos, uno a uno: una zona empareja con un rango del MISMO tipo (techo H / piso L, según su grupo de picos)
    si la intersección sobre la unión de sus velas es ≥ 0,3. Rangos superpuestos de distinto tipo se evalúan por separado.
    Precisión sobre las zonas que caen en las ventanas revisadas."""
    Zw = [z for z in Z if any(overlap(z["i0"], z["i1"], a, b) > 0 for a, b in win)]
    pairs = sorted(((iou(z["i0"], z["i1"], r["i0"], r["i1"]), zi, ri) for zi, z in enumerate(Zw) for ri, r in enumerate(R)
                    if z["kind"] == r["kind"]), reverse=True)
    used_z, used_r = set(), set()
    for v, zi, ri in pairs:
        if v < 0.3:
            break
        if zi in used_z or ri in used_r:
            continue
        used_z.add(zi); used_r.add(ri)
    rec = len(used_r) / max(len(R), 1); prec = len(used_z) / max(len(Zw), 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return f1, prec, rec, len(Zw)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", required=True); a = ap.parse_args(argv)
    lab = json.loads((VIEW / "labels" / f"{a.asset}.json").read_text(encoding="utf-8"))
    b = json.loads((VIEW / "bundles" / f"{a.asset}.json").read_text(encoding="utf-8"))
    tick = float(b["meta"]["tick_size"])
    c = b["bar_series"][next(iter(b["bar_series"]))]["candles"]
    cd = dict(t=np.array([x["time"] for x in c], float), h=np.array([x["high"] for x in c]), l=np.array([x["low"] for x in c]))
    del b, c
    # tipo de cada rango = tipo del grupo de picos que contiene (Nico: cada rango coincide con su secuencia de highs o lows)
    R = []
    for r in lab["ranges"]:
        if "i0" not in r:
            continue
        kinds = [z[0]["kind"] for z in lab["zigzags"] if z and r["i0"] - 3 <= z[0]["i"] <= r["i1"] + 3 and r["i0"] - 3 <= z[-1]["i"] <= r["i1"] + 3]
        if kinds:
            R.append(dict(r, kind=kinds[0]))
    sin_grupo = sum(1 for r in lab["ranges"] if "i0" in r) - len(R)
    if not R:
        raise SystemExit("sin rangos con grupo de picos")
    if lab.get("reviewed"):
        win = [(int(np.searchsorted(cd["t"], s["t0"])), int(np.searchsorted(cd["t"], s["t1"], "right")) - 1) for s in lab["reviewed"]]
        win_note = "sesiones marcadas como revisadas"
    else:
        a0 = min(r["i0"] for r in R); a1 = max(r["i1"] for r in R)
        t0, t1 = cd["t"][a0] - 1800, cd["t"][a1] + 600
        win = [(int(np.searchsorted(cd["t"], t0)), int(np.searchsorted(cd["t"], t1)))]
        win_note = "SUPUESTO: 30 min antes del primer rango a 10 min después del último (no hay sesiones revisadas)"
    res = []
    for W, tau, nmin, w in itertools.product(GRID["W"], GRID["tau"], GRID["nmin"], GRID["w"]):
        Z0 = zones(cd, tick, W, tau, nmin, w)
        for gap, dmin in itertools.product(GRID["gap"], GRID["dmin"]):
            Z = merge(Z0, gap, dmin)
            f1, p, r, nz = score(Z, R, win)
            res.append(dict(W=W, tau=tau, nmin=nmin, w=w, gap=gap, dmin=dmin, f1=round(f1, 3), precision=round(p, 3), cobertura=round(r, 3), zonas_en_ventana=nz))
    res.sort(key=lambda x: (-x["f1"], -x["cobertura"]))
    best = res[0]
    Z = merge(zones(cd, tick, best["W"], best["tau"], best["nmin"], best["w"]), best["gap"], best["dmin"])
    days = len(set((cd["t"] // 86400).astype(int)))
    out = dict(schema="EDGELAB_PEAKS_DET_V0", asset=a.asset, etiquetas=dict(rangos=len(R), rangos_sin_grupo=sin_grupo, grupos=len(lab["zigzags"]), revisadas=len(lab.get("reviewed", []))),
               ventana_de_ajuste=win_note, parametros=best, top5=res[:5], zonas=Z, zonas_por_dia=round(len(Z) / max(days, 1), 1),
               advertencia="ajuste con pocas etiquetas: sirve para ver el desempeño a ojo fuera de lo marcado, no como detector final")
    p = VIEW / "bundles" / "peaks_det" / f"{a.asset}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(dict(mejor=best, top5=res[:5], zonas=len(Z), por_dia=out["zonas_por_dia"], ventana=win_note), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
