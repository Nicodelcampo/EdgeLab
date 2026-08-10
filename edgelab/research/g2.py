"""Primitivas estadísticas de G2 bajo la enmienda G2-A1.

La persistencia y la decisión canónica viven en ``g2_decision.py``. Este módulo
no pretende fabricar un nulo universal: cada campaña debe generar réplicas que
rompan exactamente la relación bajo prueba y preserven sus nuisance variables.

Cambios centrales de G2-A1:

* ``mcpt`` legado queda retirado de decisiones: medía concentración temporal,
  no expectativa positiva.
* ``campaign_null_pvalue`` sólo reduce un nulo ya generado y preregistrado.
* PBO y walk-forward usan el ratio canónico ``sum_pnl_net / n_trades``.
* DSR requiere probabilidad >= 0.95 y una corrección HAC por sesión versionada.
* El IC bootstrap-t por sesión es un sexto requisito duro de composición.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from math import isfinite
from statistics import NormalDist

from edgelab.research.g2_ratio import (
    CSCV_S,
    PBO_MAX,
    pbo_ratio_cscv,
    walk_forward_ratio,
)

MCPT_MAX_P = 0.05
MCPT_MIN_PERMS = 1000
DSR_MIN = 0.95
PRIMARY_CI_MIN_LOWER = 0.0

DSR_DEPENDENCE_METHOD = "session_hac_bartlett_v1"
_DSR_METHOD_SPEC = {
    "id": DSR_DEPENDENCE_METHOD,
    "observational_unit": "session",
    "scale": "non_annualized",
    "sharpe": "mean(session_return)/population_sd(session_return)",
    "dependence": "Bartlett HAC long-run variance of centered session returns",
    "effective_n": "max(2,n/max(1,HAC_variance/sample_variance))",
    "lag_default": "floor(cuberoot(n)), bounded to [1,n-1]",
    "multiplicity": "expected maximum Sharpe with manifest N_eff",
    "tail": "P(SR_observed > expected_max_SR_under_null)",
}
DSR_METHOD_SHA256_V1 = hashlib.sha256(
    json.dumps(
        _DSR_METHOD_SPEC,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

_N = NormalDist()
_EULER = 0.5772156649015329


class G2SemanticError(ValueError):
    """La operación no representa la semántica G2 aprobable."""


@dataclass(frozen=True)
class G2Result:
    name: str
    value: float
    threshold: float
    passed: bool
    detail: str = ""

    def __str__(self):
        return "%-26s %10.4f  (umbral %.4f)  %s%s" % (
            self.name,
            self.value,
            self.threshold,
            "PASS" if self.passed else "FAIL",
            ("  — " + self.detail) if self.detail else "",
        )


@dataclass(frozen=True)
class SessionDSRResult:
    probability: float
    sharpe: float
    n_observations: int
    n_effective: float
    n_trials_effective: float
    skew: float
    kurtosis: float
    hac_lag: int
    dependence_method: str = DSR_DEPENDENCE_METHOD
    method_sha256: str = DSR_METHOD_SHA256_V1


# ---------------------------------------------------------------------------
# Utilidades deterministas
# ---------------------------------------------------------------------------
def _lcg(seed):
    """PRNG histórico, conservado para fixtures y reproducibilidad."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise G2SemanticError("seed debe ser entero")
    x = seed & 0xFFFFFFFF
    while True:
        x = (1664525 * x + 1013904223) & 0xFFFFFFFF
        yield x


def _shuffle(seq, rng):
    """Fisher-Yates determinista."""
    values = list(seq)
    for index in range(len(values) - 1, 0, -1):
        other = next(rng) % (index + 1)
        values[index], values[other] = values[other], values[index]
    return values


def _number(value, field):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isfinite(value)
    ):
        raise G2SemanticError("%s debe ser numérico finito" % field)
    return float(value)


# ---------------------------------------------------------------------------
# 1. Nulo de campaña; el generador es externo y preregistrado
# ---------------------------------------------------------------------------
def campaign_null_pvalue(observed, null_statistics):
    """Reduce estadísticas nulas preregistradas a un p-valor unilateral.

    Esta función NO genera el nulo. La campaña debe persistir ``null_id``,
    hipótesis, supuesto de intercambiabilidad, semilla, generador y digest. El
    estadístico observado y cada réplica deben usar el mismo estimando.
    """
    observed = _number(observed, "observed")
    values = tuple(_number(value, "null_statistics") for value in null_statistics)
    if len(values) < MCPT_MIN_PERMS:
        raise G2SemanticError(
            "G2 exige al menos %d réplicas nulas; recibió %d"
            % (MCPT_MIN_PERMS, len(values))
        )
    worse_or_equal = sum(value >= observed for value in values)
    return (1.0 + worse_or_equal) / (1.0 + len(values)), observed


def _ordered_session_blocks(returns, session_ids):
    if len(returns) != len(session_ids):
        raise G2SemanticError("returns y session_ids deben tener el mismo largo")
    if not returns:
        return (), ()
    order = []
    blocks = {}
    closed = set()
    sentinel = object()
    previous = sentinel
    for raw_return, session_id in zip(returns, session_ids):
        try:
            hash(session_id)
        except TypeError as exc:
            raise G2SemanticError("session_id debe ser hashable") from exc
        if session_id != previous:
            if previous is not sentinel:
                closed.add(previous)
            if session_id in closed:
                raise G2SemanticError(
                    "cada sesión debe ocupar un bloque contiguo y ordenado"
                )
            order.append(session_id)
            blocks[session_id] = []
            previous = session_id
        blocks[session_id].append(_number(raw_return, "return"))
    return tuple(order), blocks


def temporal_concentration_test(
    returns, session_ids, n_perm=MCPT_MIN_PERMS, seed=12345
):
    """Diagnóstico histórico: concentración en la primera mitad de sesiones.

    No prueba expectativa positiva y está prohibido como gate. Se conserva sólo
    para reproducir artefactos anteriores a G2-A1 y demostrar por qué fallaban.
    """
    if (
        not isinstance(n_perm, int)
        or isinstance(n_perm, bool)
        or n_perm < MCPT_MIN_PERMS
    ):
        raise G2SemanticError(
            "el diagnóstico exige >= %d permutaciones" % MCPT_MIN_PERMS
        )
    order, blocks = _ordered_session_blocks(returns, session_ids)
    if not order:
        return 1.0, 0.0
    if len(order) < 2:
        return 1.0, float(sum(returns))
    k = max(1, len(order) // 2)
    observed = sum(sum(blocks[session]) for session in order[:k])
    rng = _lcg(seed)
    worse_or_equal = 0
    for _ in range(n_perm):
        permuted = _shuffle(order, rng)
        statistic = sum(sum(blocks[session]) for session in permuted[:k])
        if statistic >= observed:
            worse_or_equal += 1
    return (1.0 + worse_or_equal) / (1.0 + n_perm), float(observed)


def mcpt(*_args, **_kwargs):
    """Retirado: el MCPT anterior no era un test de edge."""
    raise G2SemanticError(
        "mcpt() fue retirado por G2-A1: use un NullGenerator específico de "
        "campaña y campaign_null_pvalue(); para reproducibilidad histórica use "
        "temporal_concentration_test()"
    )


# ---------------------------------------------------------------------------
# 2. PBO por ratio canónico
# ---------------------------------------------------------------------------
def pbo_cscv(matrix, s=CSCV_S):
    """Compatibilidad de nombre; exige ``RatioCell`` y rankea por expectativa."""
    result = pbo_ratio_cscv(matrix, s=s)
    return result.pbo, list(result.lambdas)


# ---------------------------------------------------------------------------
# 3. Deflated Sharpe Ratio
# ---------------------------------------------------------------------------
def expected_max_sharpe(n_trials, var_sharpe):
    """Sharpe esperado del mejor de ``n_trials`` intentos bajo la nula."""
    n_trials = _number(n_trials, "n_trials")
    var_sharpe = _number(var_sharpe, "var_sharpe")
    if n_trials < 1:
        raise G2SemanticError("n_trials debe ser >= 1")
    if var_sharpe < 0:
        raise G2SemanticError("var_sharpe no puede ser negativa")
    if n_trials < 2:
        return 0.0
    standard_deviation = math.sqrt(var_sharpe)
    first = _N.inv_cdf(1 - 1.0 / n_trials)
    second = _N.inv_cdf(1 - 1.0 / (n_trials * math.e))
    return standard_deviation * (
        (1 - _EULER) * first + _EULER * second
    )


def deflated_sharpe(
    sharpe,
    n_obs,
    n_trials,
    skew=0.0,
    kurt=3.0,
    var_sharpe=None,
):
    """Probabilidad DSR; ``sharpe`` siempre es por observación, no anualizado."""
    sharpe = _number(sharpe, "sharpe")
    n_obs = _number(n_obs, "n_obs")
    n_trials = _number(n_trials, "n_trials")
    skew = _number(skew, "skew")
    kurt = _number(kurt, "kurt")
    if n_obs < 2:
        return 0.0
    if n_trials < 1:
        raise G2SemanticError("n_trials debe ser >= 1")
    if var_sharpe is None:
        var_sharpe = (
            1 - skew * sharpe + (kurt - 1) / 4.0 * sharpe**2
        ) / (n_obs - 1)
    var_sharpe = _number(var_sharpe, "var_sharpe")
    if var_sharpe <= 0:
        raise G2SemanticError("var_sharpe debe ser positiva")
    expected = expected_max_sharpe(n_trials, var_sharpe)
    return _N.cdf((sharpe - expected) / math.sqrt(var_sharpe))


def deflated_sharpe_sessions(session_returns, n_trials, hac_lag=None):
    """DSR formal sobre retornos de sesión con tamaño efectivo HAC conservador."""
    values = tuple(_number(value, "session_return") for value in session_returns)
    n = len(values)
    if n < 3:
        raise G2SemanticError("DSR formal requiere al menos 3 sesiones")
    mean = sum(values) / n
    centered = tuple(value - mean for value in values)
    second = sum(value * value for value in centered) / n
    if second <= 0:
        raise G2SemanticError("DSR indefinido: varianza de sesión no positiva")
    standard_deviation = math.sqrt(second)
    sharpe = mean / standard_deviation
    third = sum(value**3 for value in centered) / n
    fourth = sum(value**4 for value in centered) / n
    skew = third / second**1.5
    kurtosis = fourth / second**2

    if hac_lag is None:
        hac_lag = max(1, int(n ** (1.0 / 3.0)))
    if (
        not isinstance(hac_lag, int)
        or isinstance(hac_lag, bool)
        or not 0 <= hac_lag < n
    ):
        raise G2SemanticError("hac_lag debe estar entre 0 y n_sessions-1")

    long_run_variance = second
    for lag in range(1, hac_lag + 1):
        covariance = sum(
            centered[index] * centered[index - lag]
            for index in range(lag, n)
        ) / n
        weight = 1.0 - lag / (hac_lag + 1.0)
        long_run_variance += 2.0 * weight * covariance
    if not isfinite(long_run_variance):
        raise G2SemanticError("varianza HAC no finita")

    dependence_factor = max(1.0, long_run_variance / second)
    n_effective = max(2.0, n / dependence_factor)
    var_sharpe = (
        1 - skew * sharpe + (kurtosis - 1) / 4.0 * sharpe**2
    ) / (n_effective - 1)
    if var_sharpe <= 0 or not isfinite(var_sharpe):
        raise G2SemanticError("varianza del Sharpe no positiva")
    probability = deflated_sharpe(
        sharpe,
        n_effective,
        n_trials,
        skew=skew,
        kurt=kurtosis,
        var_sharpe=var_sharpe,
    )
    return SessionDSRResult(
        probability=probability,
        sharpe=sharpe,
        n_observations=n,
        n_effective=n_effective,
        n_trials_effective=float(n_trials),
        skew=skew,
        kurtosis=kurtosis,
        hac_lag=hac_lag,
    )


# ---------------------------------------------------------------------------
# 4. Walk-forward por ratio canónico
# ---------------------------------------------------------------------------
def walk_forward(per_fold, folds_ordenados, seleccionar=None):
    """Compatibilidad de nombre; selecciona y agrega por ratio de totales."""
    if seleccionar is not None:
        raise G2SemanticError(
            "G2-A1 no admite selectores ad-hoc; la métrica canónica está sellada"
        )
    result = walk_forward_ratio(per_fold, folds_ordenados)
    detail = [
        {
            "fold": row.fold,
            "ganador_in_sample": row.selected_config,
            "oos_neto": row.oos_pnl,
            "oos_n_trades": row.oos_n_trades,
            "oos_expectancy": row.oos_ratio,
            "entrenado_con": list(row.trained_with),
        }
        for row in result.selections
    ]
    return result.observed, detail


# ---------------------------------------------------------------------------
# 5. Sensibilidad paramétrica
# ---------------------------------------------------------------------------
def parameter_sensitivity(expectancies, ganador, vecinos):
    """Mediana de expectancies netas por trade de vecinos ±1 paso."""
    del ganador  # el ganador nunca se incluye en su propia vecindad
    values = [
        _number(expectancies[neighbor], "expectancy")
        for neighbor in vecinos
        if neighbor in expectancies
    ]
    if not values:
        return None, 0, 0
    values.sort()
    n = len(values)
    median = (
        values[n // 2]
        if n % 2
        else (values[n // 2 - 1] + values[n // 2]) / 2.0
    )
    return median, sum(value > 0 for value in values), n


# ---------------------------------------------------------------------------
# Composición diagnóstica; la autoridad persistida es G2ValidationDecision
# ---------------------------------------------------------------------------
def evaluar(
    *,
    null_p=None,
    pbo=None,
    dsr=None,
    wf_oos=None,
    sensibilidad_mediana=None,
    primary_ci_lower=None,
):
    """Aplica los seis requisitos de G2-A1; todo faltante falla cerrado."""
    results = [
        G2Result(
            "nulo de campaña p",
            null_p if null_p is not None else 1.0,
            MCPT_MAX_P,
            null_p is not None and null_p <= MCPT_MAX_P,
            "" if null_p is not None else "no evaluado",
        ),
        G2Result(
            "PBO",
            pbo if pbo is not None else 1.0,
            PBO_MAX,
            pbo is not None and pbo <= PBO_MAX,
            "" if pbo is not None else "no evaluado",
        ),
        G2Result(
            "DSR",
            dsr if dsr is not None else -1.0,
            DSR_MIN,
            dsr is not None and dsr >= DSR_MIN,
            "" if dsr is not None else "no evaluado",
        ),
        G2Result(
            "WF-OOS expectancy",
            wf_oos if wf_oos is not None else -1.0,
            0.0,
            wf_oos is not None and wf_oos > 0.0,
            "" if wf_oos is not None else "no evaluado",
        ),
        G2Result(
            "sensibilidad (mediana)",
            sensibilidad_mediana if sensibilidad_mediana is not None else -1.0,
            0.0,
            sensibilidad_mediana is not None and sensibilidad_mediana > 0.0,
            "" if sensibilidad_mediana is not None else "no evaluado",
        ),
        G2Result(
            "IC primario (cota inferior)",
            primary_ci_lower if primary_ci_lower is not None else -1.0,
            PRIMARY_CI_MIN_LOWER,
            primary_ci_lower is not None and primary_ci_lower > 0.0,
            "" if primary_ci_lower is not None else "no evaluado",
        ),
    ]
    return results, all(result.passed for result in results)
