"""Estimando trade-weighted con dependencia por sesión.

Primitiva candidata de la enmienda G2-2026-08-03. Remuestrear clusters no
significa dar el mismo peso económico a cada cluster: cada réplica recomputa el
ratio de totales ``sum(PnL neto) / sum(n trades)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence


class ClusterEstimandError(ValueError):
    """Inputs incompatibles con el estimando preregistrado."""


@dataclass(frozen=True)
class SessionAggregate:
    session_id: str
    pnl_net: float
    n_trades: int

    def __post_init__(self):
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ClusterEstimandError("session_id debe ser texto no vacio")
        if not isinstance(self.n_trades, int) or isinstance(self.n_trades, bool):
            raise ClusterEstimandError("n_trades debe ser entero")
        if self.n_trades < 0:
            raise ClusterEstimandError("n_trades no puede ser negativo")
        if not isinstance(self.pnl_net, (int, float)) or not isfinite(self.pnl_net):
            raise ClusterEstimandError("pnl_net debe ser finito")
        if self.n_trades == 0 and self.pnl_net != 0:
            raise ClusterEstimandError("sesion sin trades debe tener pnl_net=0")


@dataclass(frozen=True)
class ClusterBootstrapResult:
    observed: float
    replicates: tuple[float, ...]
    invalid_zero_denominator: int
    n_sessions: int
    n_trades: int
    seed: int


class _Lcg:
    """Muestreo determinista e independiente de numpy/random global."""

    def __init__(self, seed: int):
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ClusterEstimandError("seed debe ser entero")
        self.state = seed & 0xFFFFFFFF

    def index(self, n: int) -> int:
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state % n


def aggregate_sessions(
    session_ids: Sequence[str],
    trades_by_session: Mapping[str, Iterable[float]],
) -> tuple[SessionAggregate, ...]:
    """Agrega trades sobre el universo completo de sesiones elegibles.

    ``session_ids`` es el calendario preregistrado e incluye días sin trades.
    Claves de trades fuera del calendario son error: no se descartan en silencio.
    """
    if not session_ids:
        raise ClusterEstimandError("hace falta al menos una sesion elegible")
    if len(set(session_ids)) != len(session_ids):
        raise ClusterEstimandError("session_ids contiene duplicados")
    unknown = set(trades_by_session) - set(session_ids)
    if unknown:
        raise ClusterEstimandError("trades fuera del calendario: %s" % sorted(unknown))

    out = []
    for session_id in session_ids:
        values = tuple(trades_by_session.get(session_id, ()))
        if any(not isinstance(x, (int, float)) or not isfinite(x) for x in values):
            raise ClusterEstimandError("trade PnL no finito en %s" % session_id)
        out.append(SessionAggregate(session_id, float(sum(values)), len(values)))
    return tuple(out)


def trade_weighted_expectancy(clusters: Iterable[SessionAggregate]) -> float:
    """``sum_d u_d / sum_d v_d``; nunca ``mean_d(u_d/v_d)``."""
    rows = tuple(clusters)
    if not rows:
        raise ClusterEstimandError("no hay clusters")
    denominator = sum(row.n_trades for row in rows)
    if denominator == 0:
        raise ClusterEstimandError("estimando indefinido: cero trades")
    return sum(row.pnl_net for row in rows) / denominator


def resample_session_clusters(
    clusters: Sequence[SessionAggregate],
    *,
    n_replicates: int,
    seed: int,
) -> ClusterBootstrapResult:
    """Remuestrea sesiones completas y recalcula el ratio en cada réplica.

    Una réplica que sortea sólo sesiones sin trades queda registrada como
    inválida. No se convierte en cero ni se reemplaza con otro sorteo, porque
    hacerlo ocultaría la geometría real del procedimiento.
    """
    rows = tuple(clusters)
    if not rows:
        raise ClusterEstimandError("no hay clusters")
    if not isinstance(n_replicates, int) or isinstance(n_replicates, bool) or n_replicates < 1:
        raise ClusterEstimandError("n_replicates debe ser entero >= 1")
    observed = trade_weighted_expectancy(rows)
    rng = _Lcg(seed)
    values = []
    invalid = 0
    for _ in range(n_replicates):
        sampled = [rows[rng.index(len(rows))] for _ in rows]
        denominator = sum(row.n_trades for row in sampled)
        if denominator == 0:
            invalid += 1
            continue
        values.append(sum(row.pnl_net for row in sampled) / denominator)
    return ClusterBootstrapResult(
        observed=observed,
        replicates=tuple(values),
        invalid_zero_denominator=invalid,
        n_sessions=len(rows),
        n_trades=sum(row.n_trades for row in rows),
        seed=seed,
    )


def percentile_interval(result: ClusterBootstrapResult, confidence: float = 0.95):
    """Intervalo percentil diagnóstico; todavía no autorizado como gate G2."""
    if not 0 < confidence < 1:
        raise ClusterEstimandError("confidence debe estar entre 0 y 1")
    values = sorted(result.replicates)
    if len(values) < 2:
        raise ClusterEstimandError("replicas validas insuficientes")
    alpha = 1.0 - confidence

    def quantile(p):
        pos = p * (len(values) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(values) - 1)
        frac = pos - lo
        return values[lo] * (1.0 - frac) + values[hi] * frac

    return quantile(alpha / 2), quantile(1.0 - alpha / 2)
