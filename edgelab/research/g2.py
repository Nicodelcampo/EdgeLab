"""Fachada canónica de robustez estadística G2.

G2-A1 elimina dos ambigüedades históricas:

- la permutación temporal mide concentración y es sólo diagnóstico;
- PBO y walk-forward reciben ``RatioCell`` y preservan
  ``sum(pnl_net) / sum(n_trades)`` mediante :mod:`g2_protocol`.

El DSR formal por calendario vive en :mod:`g2_dsr`. No existe una segunda
función ``evaluar``: la única decisión de promoción es
``g2_decision.G2ValidationDecision``.
"""
from __future__ import annotations

from edgelab.research.g2_dsr import (
    DSR_METHOD_SHA256_V2,
    deflated_sharpe,
    deflated_sharpe_sessions,
    expected_max_sharpe,
)
from edgelab.research.g2_protocol import (
    CAMPAIGN_NULL_MAX_P,
    CAMPAIGN_NULL_MIN_REPLICATES,
    CSCV_S,
    PBO_MAX,
    campaign_null_pvalue,
    pbo_cscv,
    walk_forward,
)

TEMPORAL_CONCENTRATION_MIN_PERMS = 1000


def _lcg(seed):
    """LCG determinista, independiente de numpy y del estado global."""
    value = seed & 0xFFFFFFFF
    while True:
        value = (1664525 * value + 1013904223) & 0xFFFFFFFF
        yield value


def _shuffle(sequence, generator):
    values = list(sequence)
    for index in range(len(values) - 1, 0, -1):
        selected = next(generator) % (index + 1)
        values[index], values[selected] = values[selected], values[index]
    return values


def temporal_concentration_test(
    returns,
    session_ids,
    n_perm=TEMPORAL_CONCENTRATION_MIN_PERMS,
    seed=12345,
):
    """Diagnóstico de concentración temporal; **no es gate G2**.

    Permuta sesiones completas y compara el P&L de la primera mitad temporal.
    Un p bajo indica concentración, no evidencia de expectativa positiva.
    """
    if n_perm < TEMPORAL_CONCENTRATION_MIN_PERMS:
        raise ValueError(
            "el diagnóstico exige >= %d permutaciones"
            % TEMPORAL_CONCENTRATION_MIN_PERMS
        )
    if len(returns) != len(session_ids):
        raise ValueError("returns y session_ids deben tener el mismo largo")
    if not returns:
        return 1.0, 0.0
    blocks = {}
    for value, session_id in zip(returns, session_ids):
        blocks.setdefault(session_id, []).append(value)
    sessions = sorted(blocks)
    if len(sessions) < 2:
        return 1.0, float(sum(returns))
    half = max(1, len(sessions) // 2)
    observed = sum(sum(blocks[key]) for key in sessions[:half])
    generator = _lcg(seed)
    worse_or_equal = 0
    for _ in range(n_perm):
        permutation = _shuffle(sessions, generator)
        statistic = sum(sum(blocks[key]) for key in permutation[:half])
        worse_or_equal += statistic >= observed
    return (
        (1.0 + worse_or_equal) / (1.0 + n_perm),
        float(observed),
    )


def parameter_sensitivity(expectancies, winner, neighbours):
    """Mediana de expectativa neta de vecinos ±1 paso de grilla."""
    values = sorted(
        expectancies[neighbour]
        for neighbour in neighbours
        if neighbour in expectancies
    )
    if not values:
        return None, 0, 0
    count = len(values)
    median = (
        values[count // 2]
        if count % 2
        else (values[count // 2 - 1] + values[count // 2]) / 2.0
    )
    return median, sum(value > 0 for value in values), count


def dsr_method_sha256():
    """Alias de compatibilidad para la especificación DSR vigente."""
    return DSR_METHOD_SHA256_V2
