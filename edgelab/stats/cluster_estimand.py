"""Estimando trade-weighted con dependencia por sesión.

Primitiva candidata de la enmienda G2-2026-08-03. Remuestrear clusters no
significa dar el mismo peso económico a cada cluster: cada réplica recomputa el
ratio de totales ``sum(PnL neto) / sum(n trades)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite, sqrt
from typing import Iterable, Mapping, Sequence


MIN_STUDENTIZED_SESSIONS = 160


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
        if (not isinstance(self.pnl_net, (int, float))
                or isinstance(self.pnl_net, bool) or not isfinite(self.pnl_net)):
            raise ClusterEstimandError("pnl_net debe ser numerico finito")
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
    method: str = "iid_clusters"
    block_length: int = 1


@dataclass(frozen=True)
class StudentizedIntervalResult:
    observed: float
    lower: float
    upper: float
    standard_error: float
    confidence: float
    valid_replicates: int
    requested_replicates: int
    block_length: int
    hac_lag: int
    n_sessions: int
    n_trades: int
    seed: int
    method: str = "stationary_bootstrap_t"


class _SplitMix64:
    """PRNG local: evita usar los bits bajos débiles del LCG histórico."""

    _MASK = (1 << 64) - 1

    def __init__(self, seed: int):
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ClusterEstimandError("seed debe ser entero")
        self.state = seed & self._MASK

    def uint64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & self._MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self._MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self._MASK
        return (z ^ (z >> 31)) & self._MASK

    def index(self, n: int) -> int:
        return self.uint64() % n

    def uniform(self) -> float:
        return self.uint64() / float(1 << 64)


def aggregate_sessions(
    session_ids: Sequence[str],
    trades_by_session: Mapping[str, Iterable[float]],
) -> tuple[SessionAggregate, ...]:
    """Agrega trades sobre el universo completo de sesiones elegibles.

    ``session_ids`` es el calendario preregistrado e incluye días sin trades.
    Claves de trades fuera del calendario son error: no se descartan en silencio.
    """
    if isinstance(session_ids, (str, bytes)) or not session_ids:
        raise ClusterEstimandError("hace falta una secuencia de sesiones elegibles")
    if len(set(session_ids)) != len(session_ids):
        raise ClusterEstimandError("session_ids contiene duplicados")
    unknown = set(trades_by_session) - set(session_ids)
    if unknown:
        raise ClusterEstimandError("trades fuera del calendario: %s" % sorted(unknown))

    out = []
    for session_id in session_ids:
        values = tuple(trades_by_session.get(session_id, ()))
        if any(not isinstance(x, (int, float)) or isinstance(x, bool)
               or not isfinite(x) for x in values):
            raise ClusterEstimandError("trade PnL no numerico finito en %s" % session_id)
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
    """Remuestrea sesiones completas y recalcula el ratio en cada réplica."""
    rows = tuple(clusters)
    if not rows:
        raise ClusterEstimandError("no hay clusters")
    if not isinstance(n_replicates, int) or isinstance(n_replicates, bool) or n_replicates < 1:
        raise ClusterEstimandError("n_replicates debe ser entero >= 1")
    observed = trade_weighted_expectancy(rows)
    rng = _SplitMix64(seed)
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
        observed=observed, replicates=tuple(values),
        invalid_zero_denominator=invalid, n_sessions=len(rows),
        n_trades=sum(row.n_trades for row in rows), seed=seed,
        method="iid_clusters", block_length=1)


def ratio_influence_series(clusters: Sequence[SessionAggregate]) -> tuple[float, ...]:
    """Serie proporcional a la función de influencia del ratio E[u]/E[v]."""
    rows = tuple(clusters)
    theta = trade_weighted_expectancy(rows)
    return tuple(row.pnl_net - theta * row.n_trades for row in rows)


def stationary_block_length(clusters: Sequence[SessionAggregate]) -> int:
    """PPW2009 sobre ψ_d = u_d - theta*v_d, no sobre medias diarias."""
    from edgelab.stats.bootstrap_estacionario import largo_de_bloque_optimo
    return int(largo_de_bloque_optimo(ratio_influence_series(tuple(clusters))))


def _stationary_sample(rows, rng, block_length):
    restart_probability = 1.0 / block_length
    index = rng.index(len(rows))
    sampled = []
    for position in range(len(rows)):
        if position and rng.uniform() < restart_probability:
            index = rng.index(len(rows))
        elif position:
            index = (index + 1) % len(rows)
        sampled.append(rows[index])
    return tuple(sampled)


def resample_stationary_session_clusters(
    clusters: Sequence[SessionAggregate], *, n_replicates: int, seed: int,
    block_length: int | None = None,
) -> ClusterBootstrapResult:
    """Bootstrap estacionario de pares (u_d, v_d), con wrap circular."""
    rows = tuple(clusters)
    if not rows:
        raise ClusterEstimandError("no hay clusters")
    if not isinstance(n_replicates, int) or isinstance(n_replicates, bool) or n_replicates < 1:
        raise ClusterEstimandError("n_replicates debe ser entero >= 1")
    observed = trade_weighted_expectancy(rows)
    b = stationary_block_length(rows) if block_length is None else block_length
    if not isinstance(b, int) or isinstance(b, bool) or not 1 <= b <= len(rows):
        raise ClusterEstimandError("block_length debe estar entre 1 y n_sessions")
    rng = _SplitMix64(seed)
    values = []
    invalid = 0
    for _ in range(n_replicates):
        sampled = _stationary_sample(rows, rng, b)
        denominator = sum(row.n_trades for row in sampled)
        if denominator == 0:
            invalid += 1
            continue
        values.append(sum(row.pnl_net for row in sampled) / denominator)
    return ClusterBootstrapResult(
        observed=observed, replicates=tuple(values),
        invalid_zero_denominator=invalid, n_sessions=len(rows),
        n_trades=sum(row.n_trades for row in rows), seed=seed,
        method="stationary_session_clusters", block_length=b)


def _quantile(values, probability):
    values = sorted(values)
    position = probability * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def percentile_interval(result: ClusterBootstrapResult, confidence: float = 0.95):
    """Intervalo percentil diagnóstico; no autorizado como gate G2."""
    if not 0 < confidence < 1:
        raise ClusterEstimandError("confidence debe estar entre 0 y 1")
    if len(result.replicates) < 2:
        raise ClusterEstimandError("replicas validas insuficientes")
    alpha = 1.0 - confidence
    return (_quantile(result.replicates, alpha / 2),
            _quantile(result.replicates, 1.0 - alpha / 2))


def ratio_hac_standard_error(
    clusters: Sequence[SessionAggregate], *, lag: int,
) -> float:
    """SE Newey-West del ratio usando ψ_d=u_d-theta*v_d."""
    rows = tuple(clusters)
    n = len(rows)
    if n < 2:
        raise ClusterEstimandError("HAC requiere al menos dos sesiones")
    if not isinstance(lag, int) or isinstance(lag, bool) or not 0 <= lag < n:
        raise ClusterEstimandError("HAC lag debe estar entre 0 y n_sessions-1")
    theta = trade_weighted_expectancy(rows)
    mean_v = sum(row.n_trades for row in rows) / n
    if mean_v <= 0:
        raise ClusterEstimandError("HAC indefinido: media de trades cero")
    psi = [row.pnl_net - theta * row.n_trades for row in rows]
    long_run_variance = sum(x * x for x in psi) / n
    for k in range(1, lag + 1):
        covariance = sum(psi[t] * psi[t - k] for t in range(k, n)) / n
        long_run_variance += 2.0 * (1.0 - k / (lag + 1.0)) * covariance
    if not isfinite(long_run_variance) or long_run_variance <= 0:
        raise ClusterEstimandError("varianza HAC no positiva")
    return sqrt(long_run_variance / n) / mean_v


def studentized_stationary_interval(
    clusters: Sequence[SessionAggregate], *, n_replicates: int, seed: int,
    confidence: float = 0.95, block_length: int | None = None,
    hac_lag: int | None = None, min_valid_fraction: float = 0.90,
) -> StudentizedIntervalResult:
    """IC bootstrap-t del ratio; PPW y HAC operan sobre sesiones ordenadas."""
    rows = tuple(clusters)
    n = len(rows)
    if n < MIN_STUDENTIZED_SESSIONS:
        raise ClusterEstimandError(
            "bootstrap-t requiere al menos %d sesiones por cobertura" %
            MIN_STUDENTIZED_SESSIONS)
    if not isinstance(n_replicates, int) or isinstance(n_replicates, bool) or n_replicates < 2:
        raise ClusterEstimandError("n_replicates debe ser entero >= 2")
    if isinstance(confidence, bool) or not 0 < confidence < 1:
        raise ClusterEstimandError("confidence debe estar entre 0 y 1")
    if isinstance(min_valid_fraction, bool) or not 0 < min_valid_fraction <= 1:
        raise ClusterEstimandError("min_valid_fraction debe estar entre 0 y 1")
    b = stationary_block_length(rows) if block_length is None else block_length
    if not isinstance(b, int) or isinstance(b, bool) or not 1 <= b <= n:
        raise ClusterEstimandError("block_length debe estar entre 1 y n_sessions")
    lag = b if hac_lag is None else hac_lag
    if not isinstance(lag, int) or isinstance(lag, bool) or not 0 <= lag < n:
        raise ClusterEstimandError("HAC lag debe estar entre 0 y n_sessions-1")
    observed = trade_weighted_expectancy(rows)
    standard_error = ratio_hac_standard_error(rows, lag=lag)
    rng = _SplitMix64(seed)
    t_statistics = []
    for _ in range(n_replicates):
        sampled = _stationary_sample(rows, rng, b)
        try:
            theta_star = trade_weighted_expectancy(sampled)
            se_star = ratio_hac_standard_error(sampled, lag=lag)
        except ClusterEstimandError:
            continue
        t_statistics.append((theta_star - observed) / se_star)
    required = ceil(n_replicates * min_valid_fraction)
    if len(t_statistics) < required:
        raise ClusterEstimandError(
            "replicas studentized validas insuficientes: %d < %d" %
            (len(t_statistics), required))
    alpha = 1.0 - confidence
    q_lower = _quantile(t_statistics, alpha / 2)
    q_upper = _quantile(t_statistics, 1.0 - alpha / 2)
    return StudentizedIntervalResult(
        observed=observed, lower=observed-q_upper*standard_error,
        upper=observed-q_lower*standard_error, standard_error=standard_error,
        confidence=confidence, valid_replicates=len(t_statistics),
        requested_replicates=n_replicates, block_length=b, hac_lag=lag,
        n_sessions=n, n_trades=sum(row.n_trades for row in rows), seed=seed)
