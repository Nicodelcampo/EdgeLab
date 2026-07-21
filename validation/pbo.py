"""PBO — Probability of Backtest Overfitting via CSCV (Bailey, Borwein,
Lopez de Prado, Zhu 2015).

Entrada: matriz R (n_unidades_temporales × n_combos) de PnL por unidad
(trades cronologicos o buckets temporales). Se parte en S bloques contiguos;
para cada combinacion de S/2 bloques como IS: se elige el combo con mejor
Sharpe IS y se mide su rank relativo OOS. PBO = fraccion de combinaciones
donde el mejor IS queda BAJO la mediana OOS (lambda logit < 0).
"""
from itertools import combinations

import numpy as np


def _sharpe(x):
    x = x[~np.isnan(x).any(axis=1)] if x.ndim == 2 else x
    mu = np.nanmean(x, axis=0)
    sd = np.nanstd(x, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(sd > 0, mu / sd, -np.inf)


def pbo_cscv(R, S=10):
    """R: (T, N) PnL por unidad temporal × combo. Devuelve dict con pbo,
    lambdas y n_splits. S par (default 10 -> 252 splits)."""
    T, N = R.shape
    if N < 2 or T < S * 4:
        return {"pbo": np.nan, "n_splits": 0, "lambdas": np.array([])}
    edges = np.linspace(0, T, S + 1).astype(int)
    blocks = [R[edges[i]:edges[i + 1]] for i in range(S)]
    lambdas = []
    for is_idx in combinations(range(S), S // 2):
        is_set = set(is_idx)
        R_is = np.vstack([blocks[i] for i in range(S) if i in is_set])
        R_os = np.vstack([blocks[i] for i in range(S) if i not in is_set])
        sr_is = _sharpe(R_is)
        sr_os = _sharpe(R_os)
        best = int(np.argmax(sr_is))
        # rank relativo OOS del mejor IS (0..1)
        omega = (np.sum(sr_os <= sr_os[best]) - 1) / max(N - 1, 1)
        omega = min(max(omega, 1e-6), 1 - 1e-6)
        lambdas.append(np.log(omega / (1 - omega)))
    lambdas = np.array(lambdas)
    return {"pbo": float((lambdas < 0).mean()), "n_splits": len(lambdas),
            "lambdas": lambdas}
