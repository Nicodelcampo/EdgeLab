#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BATERÍA DE COBERTURA — auditoría de F-MET 3 antes de congelarlo.

## Qué decide esto

El pre-registro de EXPLORE-001 congela un método de inferencia. Antes de
congelarlo hay que saber si **cubre lo que dice cubrir**: un IC del 95 % que en
realidad cubre el 82 % convierte el umbral de detección en algo más permisivo de
lo declarado, y un resultado que lo cruce tiene más probabilidad de ser ruido
que el 5 % nominal.

## La batería queda DECLARADA ANTES de correrla

Procesos, tamaños, réplicas, seeds y criterios de adopción están fijados en
`BATERIA` y `CRITERIOS` abajo. Correr, mirar y después elegir qué caso "cuenta"
sería la misma búsqueda de especificación que el proyecto persigue en los datos.

Se incluyen a propósito dos procesos que **no** son AR(1):

- **ARMA(1,1)**: dependencia corta pero no puramente autorregresiva. El
  correlograma decae distinto y ahí la regla de selección de `m` se prueba de
  verdad.
- **GARCH(1,1)**: media SIN autocorrelación pero varianza agrupada. Es el caso
  que más se parece a la serie diaria real, donde `b_opt` dio 13–18. Si un
  método cubre bien acá, cubre en el caso que importa.

## Métodos comparados

- `fijo_b1`  — bloque fijo de 1 día: lo que usa el arnés HOY.
- `ppw2009`  — Politis–White 2004 corregido por Patton–Politis–White 2009. La
               implementación está en `edgelab.stats.bootstrap_estacionario`
               (`largo_de_bloque_optimo`) y las ecuaciones en
               `docs/referencias/PPW2009_BLOQUE_OPTIMO.md`.

Uso:  .venv/Scripts/python tools/bateria_cobertura_bootstrap.py [--sims 1000]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.stats.bootstrap_estacionario import (bootstrap_bloque_fijo,  # noqa: E402
                                                  bootstrap_estacionario,
                                                  largo_de_bloque_optimo)

SEED_BASE = 20260728          # declarada

# ---------------------------------------------------------------------------
# PROCESOS. Todos con media verdadera 0, para que la cobertura sea comprobable.
# ---------------------------------------------------------------------------
def iid_normal(n, r):
    return r.standard_normal(n)


def iid_t3(n, r):
    """t-Student de 3 gl: colas pesadas, varianza finita."""
    x = r.standard_t(3, size=n)
    return x / np.sqrt(3.0)


def ar1(phi):
    def f(n, r):
        e = r.standard_normal(n)
        x = np.empty(n)
        x[0] = e[0] / np.sqrt(1 - phi * phi)
        for t in range(1, n):
            x[t] = phi * x[t - 1] + e[t]
        return x
    return f


def arma11(phi=0.5, theta=0.4):
    """Dependencia corta NO puramente AR: el correlograma decae distinto."""
    def f(n, r):
        e = r.standard_normal(n + 1)
        x = np.empty(n)
        x[0] = e[1]
        for t in range(1, n):
            x[t] = phi * x[t - 1] + e[t + 1] + theta * e[t]
        return x
    return f


def garch11(omega=0.05, alpha=0.10, beta=0.85):
    """Media SIN autocorrelacion, varianza AGRUPADA. El caso que mas se parece
    a la serie diaria real (volatilidad por semanas)."""
    def f(n, r):
        e = r.standard_normal(n)
        s2 = np.empty(n)
        x = np.empty(n)
        s2[0] = omega / max(1e-9, 1 - alpha - beta)
        x[0] = np.sqrt(s2[0]) * e[0]
        for t in range(1, n):
            s2[t] = omega + alpha * x[t - 1] ** 2 + beta * s2[t - 1]
            x[t] = np.sqrt(s2[t]) * e[t]
        return x
    return f


BATERIA = [
    ("iid_normal",   iid_normal),
    ("iid_t3",       iid_t3),
    ("ar1_0.2",      ar1(0.2)),
    ("ar1_0.5",      ar1(0.5)),
    ("ar1_0.8",      ar1(0.8)),
    ("arma11",       arma11()),
    ("garch11",      garch11()),
]
TAMANOS = [160, 197, 250]
NOMINALES = [0.90, 0.95]

# Criterios de adopcion PREDECLARADOS (del pedido de Nico, 2026-07-28)
CRITERIOS = dict(
    iid_ic95=(0.93, 0.97),
    ar_phi_bajo_min=0.92,     # phi <= 0.5
    ar_phi_alto_min=0.90,     # phi = 0.8
)


def cobertura(gen, n, metodo, sims, reps, alpha, b=None):
    """Fraccion de veces que el IC contiene la media verdadera (= 0)."""
    dentro = 0
    for i in range(sims):
        r = np.random.default_rng(SEED_BASE + i)
        x = gen(n, r)
        res = metodo(x, reps=reps, b=b, seed=SEED_BASE + i, alpha=alpha)
        if res and res["ic"][0] <= 0.0 <= res["ic"][1]:
            dentro += 1
    return dentro / sims


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=1000)
    ap.add_argument("--reps", type=int, default=400)
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "cobertura_bootstrap.json"))
    a = ap.parse_args(argv)

    print("BATERIA DE COBERTURA — declarada antes de correr")
    print("  procesos: %s" % [p for p, _ in BATERIA])
    print("  n: %s   nominales: %s   sims: %d   reps: %d   seed: %d"
          % (TAMANOS, NOMINALES, a.sims, a.reps, SEED_BASE))
    print("  metodos: fijo_b1, ppw2009")
    print()

    filas = []
    print("%-12s %5s %6s %10s %10s   %s" % ("proceso", "n", "nominal", "fijo_b1", "ppw2009", "b_opt mediana"))
    for nombre, gen in BATERIA:
        for n in TAMANOS:
            r = np.random.default_rng(SEED_BASE)
            bs = np.array([largo_de_bloque_optimo(gen(n, r)) for _ in range(200)])
            for nom in NOMINALES:
                al = 1 - nom
                cf = cobertura(gen, n, bootstrap_bloque_fijo, a.sims, a.reps, al, b=1)
                cp = cobertura(gen, n, bootstrap_estacionario, a.sims, a.reps, al)
                filas.append(dict(proceso=nombre, n=n, nominal=nom,
                                  cob_fijo_b1=cf, cob_ppw2009=cp,
                                  b_opt_mediana=float(np.median(bs)),
                                  b_opt_media=float(bs.mean()),
                                  b_opt_pct_1=float((bs == 1).mean())))
                print("%-12s %5d %6.2f %10.3f %10.3f   %.1f" % (nombre, n, nom, cf, cp, np.median(bs)))
    json.dump(dict(seed=SEED_BASE, sims=a.sims, reps=a.reps,
                   criterios=CRITERIOS, filas=filas),
              open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print()
    print("salida: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
