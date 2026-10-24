#!/usr/bin/env python3
"""Benchmark reproducible del núcleo de grilla masiva (2026-10-24). Datos sintéticos, sin mercado: mide tiempo, no edges.

  python tools/bench_grilla.py                       # escala AREAS-EXP-1 (~2 M celdas), 2 M operaciones, B = 200 y 1000
  python tools/bench_grilla.py --ops 8000000 --b 1000 --b-viejo 3 --json salida.json

Compara Romano-Wolf actual (pares sesión x celda + producto matricial) contra la implementación anterior (un tensor denso por
réplica, `grilla_masiva._medias_bootstrap_denso`). La anterior es lineal en B: se mide con `--b-viejo` réplicas y se extrapola
(se informa como extrapolación). También mide `estadisticas` y el simulador genérico fila por fila contra `niveles_lote`.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.research import grilla_generica as GG  # noqa: E402
from edgelab.research import grilla_masiva as GM  # noqa: E402

# Forma de AREAS-EXP-1: N x W x X x ejecución (grupo), A/H (ge), comercio (le), p_vol (eq_any), tercio (extremos)
PERILLAS = [GM.Perilla("N", 3), GM.Perilla("W", 4), GM.Perilla("X", 3), GM.Perilla("ejecución", 108), GM.Perilla("A/H", 4, "ge"),
            GM.Perilla("comercio", 4, "le"), GM.Perilla("p_vol", 3, "eq_any"), GM.Perilla("tercio", 3, "extremos")]


def datos(n_ops, n_ses, seed=0):
    rng = np.random.default_rng(seed)
    idx = [rng.integers(0, p.niveles, n_ops) for p in PERILLAS]
    ses = np.sort(rng.integers(0, n_ses, n_ops))
    x = rng.normal(0, 1, n_ops) + rng.normal(0, 0.3, n_ses)[ses]; x[rng.random(n_ops) < 0.1] = np.nan
    return idx, x, ses


def _t(f):
    a = time.perf_counter(); r = f(); return r, time.perf_counter() - a


class _Exp:
    NOMBRE = "BENCH"; EJECUCIONES = [(d, m) for d in (1, -1) for m in (0.5, 1.0, 2.0, 3.0)]

    @staticmethod
    def niveles(r, ej, ctx):
        d, m = ej; k = int(r["k"]); e = float(ctx["c"][k]); a = float(r["a"])
        if a < 1: return None
        return k, 0, d, e, e - d * a, e + d * m * a, 0

    @staticmethod
    def niveles_lote(D, ej, ctx):
        d, m = ej; k = D.k.to_numpy(); e = ctx["c"][k]; a = D.a.to_numpy(float)
        X = np.column_stack([k, np.zeros(len(D)), np.full(len(D), d), e, e - d * a, e + d * m * a, np.zeros(len(D))]).astype(float)
        X[~(a >= 1), 0] = np.nan
        return X


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", type=int, default=2_000_000); ap.add_argument("--sesiones", type=int, default=250)
    ap.add_argument("--b", type=int, nargs="+", default=[200, 1000]); ap.add_argument("--b-viejo", type=int, default=3)
    ap.add_argument("--disparos", type=int, default=100_000); ap.add_argument("--json")
    a = ap.parse_args()
    out = dict(plataforma=platform.platform(), python=sys.version.split()[0], ops=a.ops, sesiones=a.sesiones,
               celdas=int(np.prod([p.tamano_celdas() for p in PERILLAS])))
    idx, x, ses = datos(a.ops, a.sesiones)
    (S, Q, C), tt = _t(lambda: GM.tensor(PERILLAS, idx, x)); out["tensor_s"] = round(tt, 2)
    st, te = _t(lambda: GM.estadisticas(S, Q, C)); out["estadisticas_s"] = round(te, 2); out["evaluables"] = int(st["evaluable"].sum())
    GM.romano_wolf(PERILLAS, [i[:5000] for i in idx], x[:5000], ses[:5000], GM.estadisticas(*GM.tensor(PERILLAS, [i[:5000] for i in idx], x[:5000])), B=2)  # compila
    ev = st["evaluable"].ravel(); us, inv = np.unique(ses, return_inverse=True)
    W = np.random.default_rng(1).multinomial(len(us), np.full(len(us), 1 / len(us)), size=a.b_viejo).astype(float)
    _, tv = _t(lambda: GM._medias_bootstrap_denso(PERILLAS, idx, x, inv, ev, W))
    out["rw_viejo_por_replica_s"] = round(tv / a.b_viejo, 3)
    out["rw"] = []
    for B in a.b:
        r, tn = _t(lambda: GM.romano_wolf(PERILLAS, idx, x, ses, st, B=B, alfa=0.10, seed=7))
        viejo = tv / a.b_viejo * B
        out["rw"].append(dict(B=B, nuevo_s=round(tn, 2), viejo_extrapolado_s=round(viejo, 1), aceleracion=round(viejo / tn, 1),
                              rechazadas=len(r["rechazadas"])))
        print(f"Romano-Wolf B={B}: nuevo {tn:.1f}s, anterior ~{viejo:.0f}s (extrapolado de {a.b_viejo} réplicas) -> x{viejo / tn:.0f}", flush=True)
    # simulador genérico: armado de operaciones fila por fila contra niveles_lote
    rng = np.random.default_rng(2); n = 200_000; ctx = dict(c=20000 + np.cumsum(rng.choice([-0.25, 0, 0.25], n)), tick=0.25)
    D = pd.DataFrame(dict(k=rng.integers(0, n, a.disparos), a=rng.uniform(0, 8, a.disparos)))
    O1, t1 = _t(lambda: GG.ops_por_fila(_Exp, D, ctx)); O2, t2 = _t(lambda: GG._ops_lote(_Exp, D, ctx))
    assert np.array_equal(O1, O2)
    out["niveles"] = dict(disparos=a.disparos, ejecuciones=len(_Exp.EJECUCIONES), operaciones=len(O1), fila_por_fila_s=round(t1, 2),
                          lote_s=round(t2, 3), aceleracion=round(t1 / t2, 1))
    print(f"niveles: fila por fila {t1:.1f}s, en lote {t2:.2f}s -> x{t1 / t2:.0f} ({len(O1)} operaciones, idénticas)")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if a.json: Path(a.json).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
