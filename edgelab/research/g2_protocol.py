"""Primitivas canónicas de G2 que faltaban en la primera enmienda A1.

No existe un MCPT universal: cada campaña genera su propio nulo y este módulo
sólo aplica la reducción finita. PBO y walk-forward delegan a las primitivas de
ratio de totales; nunca rankean por P&L total.
"""
from __future__ import annotations

from math import isfinite

from edgelab.research.g2_ratio import (
    CSCV_S,
    PBO_MAX,
    pbo_ratio_cscv,
    walk_forward_ratio,
)

CAMPAIGN_NULL_MAX_P = 0.05
CAMPAIGN_NULL_MIN_REPLICATES = 1000


class G2ProtocolError(ValueError):
    """La operación cambiaría o inventaría la semántica G2."""


def _number(value, field):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isfinite(value)
    ):
        raise G2ProtocolError("%s debe ser numérico finito" % field)
    return float(value)


def campaign_null_pvalue(observed, null_statistics):
    """P-valor unilateral finito para un nulo generado por la campaña.

    La campaña persiste ``null_id``, hipótesis, nuisance preservado, supuesto de
    intercambiabilidad, generador, seed y digest. Esta función no genera ni
    elige el nulo después de ver resultados.
    """
    observed = _number(observed, "observed")
    values = tuple(_number(value, "null_statistics") for value in null_statistics)
    if len(values) < CAMPAIGN_NULL_MIN_REPLICATES:
        raise G2ProtocolError(
            "G2 exige al menos %d réplicas nulas; recibió %d"
            % (CAMPAIGN_NULL_MIN_REPLICATES, len(values))
        )
    worse_or_equal = sum(value >= observed for value in values)
    return (1.0 + worse_or_equal) / (1.0 + len(values)), observed


def pbo_cscv(matrix, *, s=CSCV_S):
    """PBO canónico por ``sum_pnl_net / n_trades``."""
    return pbo_ratio_cscv(matrix, s=s)


def walk_forward(per_fold, folds_ordered):
    """Walk-forward canónico con selección y agregado por ratio de totales."""
    return walk_forward_ratio(per_fold, folds_ordered)
