#!/usr/bin/env python3
r"""Detector de «picos consecutivos» v2 — regla de Nico: **cada pico no supera al anterior**.

    .venv\Scripts\python tools\peaks_rule.py --asset ES_03-26_202601_25T_HFT

Regla (verificada sobre las 21 series marcadas por Nico: 0 de 254 pares la violan, ni por 1 tick, ni entre picos):
- highs: cada máximo ≤ el anterior, y ninguna vela entre ambos lo supera; lows: cada mínimo ≥ el anterior, ídem.
  La serie puede ser horizontal o escalonada a favor.
- Parámetros: pivote de `w` velas por lado (confirmado `w` velas después: causal); separación máxima entre picos
  `max_gap` velas; escalón máximo `max_step` ticks; retroceso mínimo entre picos `min_pull` ticks; `nmin` picos.
- La serie termina cuando el precio supera al último pico (ruptura), cuando pasan `max_gap` velas sin nuevo pico o en
  la pausa de sesión. Se emite si tiene ≥ `nmin` picos.
- Ajuste a las marcas con el mismo puntaje uno a uno por tipo (IoU ≥ 0,3) que `peaks_learn.py`, y control **entre
  sesiones** (ajusta en una, prueba en la otra).
Salida: `bundles/peaks_det/<asset>.json` (esquema V2, con los picos de cada serie) para la capa y el modo ✓/✗.
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
sys.path.insert(0, str(REPO / "tools"))
import peaks_learn as P  # noqa: E402

VIEW = P.VIEW
GRID = dict(w=(1, 2, 3), max_gap=(15, 30, 60, 110), max_step=(0, 2, 4, 6), min_pull=(0, 1, 2), nmin=(4, 6, 8, 10))


@njit(cache=True)
def chains(h, l, t, tick, w, max_gap, max_step, min_pull, nmin, kind):
    """Series (i0, i_fin, n) y pertenencia de cada pico a su serie. kind 1 = highs, -1 = lows (se trabaja como techo)."""
    n = len(h)
    x = h if kind == 1 else -l
    y = l if kind == 1 else -h                        # lado opuesto en el espacio «techo», para el retroceso entre picos
    piv = np.zeros(n, np.bool_)
    for q in range(w, n - w):
        ok = True
        for o in range(1, w + 1):
            if x[q] < x[q - o] or x[q] < x[q + o]:
                ok = False
                break
        piv[q] = ok
    member = np.full(n, -1, np.int64)
    out = np.zeros((n // 4 + 10, 3))
    m = 0
    cur = np.zeros(n, np.int64)                      # índices de la serie en curso
    k = 0
    last = -1; P = 0.0; lowbetween = 1e18
    for j in range(w, n):
        brk = False
        if k > 0 and (t[j] - t[j - 1] > 1800):
            brk = True
        if k > 0 and not brk:
            if x[j] > P + 1e-9 and j > last:       # el precio supera al último pico: ruptura
                brk = True
            elif j - last > max_gap:
                brk = True
        if brk:
            if k >= nmin:
                out[m, 0] = cur[0]; out[m, 1] = j; out[m, 2] = k
                for u in range(k):
                    member[cur[u]] = m
                m += 1
            k = 0; last = -1
        # pivote confirmado en esta vela: q = j - w
        q = j - w
        if q > last and q >= 0 and piv[q]:
            if k == 0:
                cur[0] = q; k = 1; last = q; P = x[q]; lowbetween = 1e18
            else:
                mn = 1e18                              # extremo opuesto entre picos (en el espacio «techo»: y = l o −h)
                for r in range(last + 1, q):
                    mn = min(mn, y[r])
                pull = (P - mn) / tick if mn < 1e17 else 0.0
                step = (P - x[q]) / tick
                if x[q] <= P + 1e-9 and step <= max_step and pull >= min_pull:
                    cur[k] = q; k += 1; last = q; P = x[q]
                # si no: pico menor (escalón grande) o sin retroceso previo → se ignora y la serie sigue, como en las
                # marcas de Nico, que no marcan los rebotes chicos; sólo la corta la ruptura o el tiempo sin pico válido
    return out[:m], member


def backfill(pk, x, piv, t, tick, max_gap, max_step):
    """Extiende la serie hacia atrás (pedido de Nico, 26/09): prepende picos anteriores que cumplen la regla respecto del
    primero (igual o más alto en el espacio «techo», escalón ≤ max_step, ninguna vela intermedia lo supera, misma sesión).
    Causal: sólo usa velas anteriores al primer pico."""
    first = pk[0]
    while True:
        best = -1
        for q in range(first - 1, max(first - max_gap, 0) - 1, -1):
            if t[q + 1] - t[q] > 1800:
                break
            if not piv[q]:
                continue
            step = (x[q] - x[first]) / tick
            if -1e-9 <= step <= max_step and x[q + 1:first].max(initial=-1e18) <= x[q] + 1e-9:
                best = q
                break
        if best < 0:
            return pk
        pk = [best] + pk
        first = best


def pivots(x, w):
    n = len(x); piv = np.zeros(n, bool)
    for o in range(1, w + 1):
        pass
    core = np.ones(n - 2 * w, bool)
    for o in range(1, w + 1):
        core &= (x[w:n - w] >= x[w - o:n - w - o]) & (x[w:n - w] >= x[w + o:n - w + o])
    piv[w:n - w] = core
    return piv


def series(cd, tick, w, max_gap, max_step, min_pull, nmin, extend_back=False):
    Z = []
    for kind in (1, -1):
        rows, member = chains(cd["h"], cd["l"], cd["t"], tick, w, max_gap, max_step, min_pull, nmin, kind)
        src = cd["h"] if kind == 1 else cd["l"]
        xx = cd["h"] if kind == 1 else -cd["l"]
        piv = pivots(xx, w) if extend_back else None
        by = {}
        for q in np.flatnonzero(member >= 0):
            by.setdefault(int(member[q]), []).append(int(q))
        for zi, r in enumerate(rows):
            pk = by.get(zi, [])
            if len(pk) < nmin:
                continue
            if extend_back:
                pk = backfill(pk, xx, piv, cd["t"], tick, max_gap, max_step)
            i0, i1 = int(pk[0]), int(r[1])
            pr = src[pk]
            Z.append(dict(kind="H" if kind == 1 else "L", i0=i0, i1=i1, t0=float(cd["t"][i0]), t1=float(cd["t"][i1]),
                          p0=float(pr.min()), p1=float(pr.max()), toques=len(pk),
                          picos=[[q, float(cd["t"][q]), float(src[q])] for q in pk]))
    return Z


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", required=True)
    ap.add_argument("--reuse-best", action="store_true", help="no buscar en la grilla: reusar los parámetros del último ajuste")
    a = ap.parse_args(argv)
    lab = json.loads((VIEW / "labels" / f"{a.asset}.json").read_text(encoding="utf-8"))
    b = json.loads((VIEW / "bundles" / f"{a.asset}.json").read_text(encoding="utf-8"))
    tick = float(b["meta"]["tick_size"])
    c = b["bar_series"][next(iter(b["bar_series"]))]["candles"]
    cd = dict(t=np.array([x["time"] for x in c], float), h=np.array([x["high"] for x in c]), l=np.array([x["low"] for x in c]))
    del b, c
    R = []
    for r in lab["ranges"]:
        if "i0" not in r:
            continue
        k = [z[0]["kind"] for z in lab["zigzags"] if z and r["i0"] - 3 <= z[0]["i"] <= r["i1"] + 3 and r["i0"] - 3 <= z[-1]["i"] <= r["i1"] + 3]
        if k:
            R.append(dict(r, kind=k[0]))
    gaps = np.flatnonzero(np.diff(cd["t"]) > 1800) + 1
    so = np.searchsorted(gaps, np.arange(len(cd["t"])), side="right")
    S = sorted({int(so[r["i0"]]) for r in R})

    def win_of(rs):
        return [(int(np.searchsorted(cd["t"], cd["t"][min(r["i0"] for r in rs)] - 1800)),
                 int(np.searchsorted(cd["t"], cd["t"][max(r["i1"] for r in rs)] + 600)))]
    wins_all = [wn for s in S for wn in win_of([r for r in R if so[r["i0"]] == s])]
    outp = VIEW / "bundles" / "peaks_det" / f"{a.asset}.json"
    if a.reuse_best and outp.exists():
        prev = json.loads(outp.read_text(encoding="utf-8"))
        best = prev["parametros"]
        Z = series(cd, tick, *[best[k] for k in GRID], extend_back=True)
        f1, pr, rc, nz = P.score(Z, R, wins_all)
        prev.update(zonas=Z, extension_atras=True, puntaje_con_extension=dict(f1=round(f1, 3), precision=round(pr, 3), cobertura=round(rc, 3), zonas_en_ventana=nz))
        outp.write_text(json.dumps(prev, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(json.dumps(dict(parametros={k: best[k] for k in GRID}, con_extension=prev["puntaje_con_extension"], sin_extension={k: best[k] for k in ("f1", "precision", "cobertura")}), ensure_ascii=False))
        return
    res = []                                         # sólo puntajes: guardar las zonas de 576 combinaciones colgó la PC (26/09)
    for w, mg, ms, mp, nm in itertools.product(*GRID.values()):
        Z = series(cd, tick, w, mg, ms, mp, nm)
        f1, pr, rc, nz = P.score(Z, R, wins_all)
        per = {}
        for s in S:
            rs = [r for r in R if so[r["i0"]] == s]
            per[s] = P.score(Z, rs, win_of(rs))
        res.append(dict(w=w, max_gap=mg, max_step=ms, min_pull=mp, nmin=nm, f1=round(f1, 3), precision=round(pr, 3), cobertura=round(rc, 3),
                        zonas_en_ventana=nz, por_sesion={int(s): [round(v, 3) for v in per[s][:3]] for s in S}))
    res.sort(key=lambda r: (-r["f1"], -r["cobertura"]))
    # validación entre sesiones: elegir en una, medir en la otra
    cruz = []
    for te in S:
        tr = [s for s in S if s != te]
        best = max(res, key=lambda r: np.mean([r["por_sesion"][s][0] for s in tr]))
        cruz.append(dict(prueba=int(te), params={k: best[k] for k in GRID}, f1=best["por_sesion"][te][0], precision=best["por_sesion"][te][1],
                         cobertura=best["por_sesion"][te][2]))
    best = res[0]
    del Z
    Z = series(cd, tick, *[best[k] for k in GRID], extend_back=True)
    days = len(set((cd["t"] // 86400).astype(int)))
    out = dict(schema="EDGELAB_PEAKS_DET_V2_REGLA", asset=a.asset, regla="cada pico no supera al anterior (highs ≤, lows ≥), sin superación entre picos",
               parametros=best, top5=res[:5], validacion_entre_sesiones=cruz, zonas=Z, zonas_por_dia=round(len(Z) / max(days, 1), 1),
               supuesto="precisión con ventana supuesta revisada (zonas grises sin marcar): está subestimada")
    (VIEW / "bundles" / "peaks_det" / f"{a.asset}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(dict(mejor=best, validacion_entre_sesiones=cruz, zonas=len(Z), por_dia=out["zonas_por_dia"]), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
