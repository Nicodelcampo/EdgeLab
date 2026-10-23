"""Controles estándar del embudo (2026-10-23): corren para TODA campaña que llega a la compuerta de integridad, sin escribir nada.

- alineación al segundo entre el activo de la señal y el de ejecución (si son distintos): pico en <= 0 s, o es look-ahead;
- placebo: la misma geometría (distancias a objetivo y stop) en momentos y direcciones al azar de la misma sesión, debe dar
  ≈ −fricción; si se parece a la regla, el resultado viene de la geometría o del simulador;
- latencia: la misma orden 1, 2 y 5 velas tarde (con `grilla_generica.correr(retraso=...)`): un edge real se degrada suave.
Origen: U1-CRUZADO (`docs/research/areas_expansion_20261022/u1/PREREGISTRO_INTEGRIDAD_Y_OOS_U1_CRUZADO.md`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX


def alineacion_segundos(bloques_a, bloques_b, max_dias: int = 30, lags=range(-20, 21)) -> dict:
    """Correlación de retornos por segundo; lag > 0 = b va detrás de a. Pico en > 0 con a = señal sería look-ahead."""
    def serie(bloques):
        out = []
        for i, b in enumerate(bloques):
            if i >= max_dias: break
            out.append(pd.Series(b.px.to_numpy(float), index=b.ts_ns.to_numpy() // 1_000_000_000).groupby(level=0).last())
        return pd.concat(out) if out else pd.Series(dtype=float)
    a, b = serie(bloques_a), serie(bloques_b)
    idx = a.index.intersection(b.index)
    if len(idx) < 1000: return dict(segundos_comunes=int(len(idx)), pico_lag_s=None, lectura="sin datos comunes suficientes")
    grid = np.arange(idx.min(), idx.max() + 1)
    ra, rb = a.reindex(grid).ffill().diff(), b.reindex(grid).ffill().diff(); viva = pd.Series(grid, index=grid).isin(idx)
    corr = {}
    for L in lags:
        x, y = ra, rb.shift(-L); m = viva & x.notna() & y.notna()
        corr[int(L)] = float(np.corrcoef(x[m], y[m])[0, 1]) if m.sum() > 100 else float("nan")
    pico = max(corr, key=lambda k: corr[k] if np.isfinite(corr[k]) else -9)
    return dict(segundos_comunes=int(len(idx)), corr=corr, pico_lag_s=pico,
                lectura="pico en 0 o negativo: sin look-ahead" if pico <= 0 else "pico positivo: la señal adelanta a la ejecución, revisar relojes")


def placebo(O, mascara, sim, seed: int = 0, separacion: int = 30) -> np.ndarray:
    """O: matriz de operaciones de `simular_ops(devolver_O=True)` (ya en el espacio de ejecución); `mascara`: las de la celda.
    Cada una se reubica al azar en la misma sesión (>= `separacion` velas de la original) con dirección al azar y la misma
    geometría. Devuelve el P&L bruto por operación placebo."""
    rng = np.random.default_rng(seed); ses = sim["ses"]; tk = sim["tick"]; filas = []
    for r in np.flatnonzero(mascara):
        j0 = int(O[r, 2]); cand = np.flatnonzero((ses == ses[j0]) & (np.abs(np.arange(len(ses)) - j0) >= separacion)); cand = cand[cand < len(ses) - 1]
        if not len(cand): continue
        j = int(rng.choice(cand)); s = int(rng.choice([-1, 1])); e = float(sim["c"][j])
        dtp, dst = abs(O[r, 7] - O[r, 5]), abs(O[r, 5] - O[r, 6])
        tp = np.round((e + s * dtp) / tk) * tk; st = e - s * dst; st = np.floor(st / tk) * tk if s == 1 else np.ceil(st / tk) * tk
        if dtp >= tk and dst >= tk: filas.append((j, s, e, st, tp))
    if not filas: return np.zeros(0)
    F = np.array(filas, float)
    pnl, _ = AX.simular(F[:, 0].astype(np.int64), F[:, 1].astype(np.int64), np.full(len(F), 2, np.int64), F[:, 2], F[:, 3], F[:, 4],
                        np.zeros(len(F), np.int64), sim["o"], sim["h"], sim["l"], sim["c"], ses, tk, sim["tpx"], sim["tstart"])
    return pnl
