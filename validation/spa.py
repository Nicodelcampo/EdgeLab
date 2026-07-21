"""SPA de Hansen (Reality Check de White) — wrapper fino sobre `arch`.

Uso: cuando hay una FAMILIA de variantes/estrategias contra un benchmark
(ej. PnL diario de K variantes vs 0), spa_pvalue devuelve el p-value
consistente de que la MEJOR no supera al benchmark tras corregir
data-snooping.
"""
import numpy as np

try:
    from arch.bootstrap import SPA
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False


def spa_pvalue(benchmark_losses, models_losses, reps=1000, seed=7):
    """benchmark_losses: (T,) perdidas del benchmark (ej. ceros).
    models_losses: (T, K) perdidas de cada variante (¡perdidas: menor=mejor!).
    Devuelve p-value consistente o NaN si arch no esta instalada."""
    if not HAS_ARCH:
        return np.nan
    spa = SPA(np.asarray(benchmark_losses, dtype=np.float64),
              np.asarray(models_losses, dtype=np.float64), reps=reps, seed=seed)
    spa.compute()
    return float(spa.pvalues["consistent"])
