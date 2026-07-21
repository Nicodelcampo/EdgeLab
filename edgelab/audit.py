"""Primitivos de auditoria estadistica (copiados de scripts/deflated_audit.py y
magnet_backtest.py del ecosistema — aislamiento EdgeLab, cero imports viejos).

deflated_sharpe : PSR(sr | sr0) de Bailey & Lopez de Prado (sr POR TRADE).
sr0_haircut     : Sharpe esperado del mejor de n_trials bajo la nula.
benjamini_hochberg : mascara de descubrimientos a FDR q.
"""
import math
from statistics import NormalDist

import numpy as np

_N = NormalDist()
PHI = _N.cdf
PHI_INV = _N.inv_cdf
EULER_GAMMA = 0.5772156649015329
DSR_PASS = 0.95


def deflated_sharpe(sr, n, skew, kurt, sr0):
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 1e-12 or n < 2:
        return np.nan
    z = (sr - sr0) * math.sqrt(n - 1) / math.sqrt(denom)
    return PHI(z)


def sr0_haircut(sd_sr, n_trials):
    if n_trials < 2 or sd_sr <= 0:
        return 0.0
    return sd_sr * ((1 - EULER_GAMMA) * PHI_INV(1 - 1.0 / n_trials)
                    + EULER_GAMMA * PHI_INV(1 - 1.0 / (n_trials * math.e)))


def benjamini_hochberg(pvals, q):
    p = np.asarray(pvals, dtype=np.float64)
    m = len(p)
    order = np.argsort(p)
    thresh = q * (np.arange(1, m + 1) / m)
    passed = p[order] <= thresh
    if not passed.any():
        return np.zeros(m, dtype=bool)
    kmax = np.max(np.flatnonzero(passed))
    cutoff = p[order][kmax]
    return p <= cutoff


def trade_stats(x):
    """Momentos por-trade de un array de PnL neto (ticks). Devuelve dict."""
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2:
        return {"n": n, "exp": np.nan, "sharpe": np.nan, "skew": np.nan, "kurt": np.nan}
    mean, sd = x.mean(), x.std()
    if sd <= 0:
        return {"n": n, "exp": mean, "sharpe": np.nan, "skew": np.nan, "kurt": np.nan}
    return {"n": n, "exp": mean, "sharpe": mean / sd,
            "skew": float(((x - mean) ** 3).mean() / sd ** 3),
            "kurt": float(((x - mean) ** 4).mean() / sd ** 4),
            "win": float((x > 0).mean())}
