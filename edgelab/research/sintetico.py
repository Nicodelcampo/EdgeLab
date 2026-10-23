"""Datos sintéticos de ticks para controles y preflight (ruido puro o con un efecto de reversión plantado).

Antes vivían dentro de un test; el preflight de cualquier experimento nuevo los necesita sin depender de los tests.
Formato de salida = el de los lectores de `fuentes_ticks` (bloques diarios: ts_ns, px, vol, sesion, segmento).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def bloques(dias=40, seed=1, planta=True, prob_salto=0.005, fuerza=0.03, tick=0.25):
    rng = np.random.default_rng(seed); t0 = 1_760_000_000 * 10**9; nivel = 20000.0
    for d in range(dias):
        n = 23 * 60 * 6; ts = t0 + d * 86400 * 10**9 + np.sort(rng.integers(0, 23 * 3600 * 10**9, n))
        paso = rng.choice([-tick, 0.0, tick], n, p=[.33, .34, .33])
        saltos = rng.random(n) < prob_salto
        paso[saltos] += rng.choice([-1, 1], saltos.sum()) * rng.integers(60, 160, saltos.sum()) * tick
        p = nivel + np.cumsum(paso)                                  # el precio CONTINÚA entre días (error 26: reiniciarlo en 20000 cada
                                                                     # día fabricaba reversión hacia el nivel inicial: el «ruido» no era ruido)
        if planta:                                                     # reversión hacia el nivel previo al salto (efecto plantado)
            ancla = pd.Series(np.where(saltos, np.r_[p[0], p[:-1]], np.nan)).ffill().fillna(p[0]).to_numpy()
            q = np.empty(n); q[0] = p[0]
            for i in range(1, n): q[i] = q[i - 1] + paso[i] + fuerza * (ancla[i] - q[i - 1])
            p = q
        nivel = float(p[-1])
        yield pd.DataFrame(dict(ts_ns=ts, px=np.round(p / tick) * tick, vol=rng.integers(1, 6, n).astype(float), sesion=np.full(n, d), segmento=np.zeros(n, int)))
