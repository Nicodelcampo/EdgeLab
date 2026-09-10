"""DSR por sesión calibrable y ligado a calendario para G2-A1.

Este módulo endurece la enmienda ya presente en ``g2.py`` sin depender de una
serie de trades filtrada. El universo es el calendario completo de sesiones
elegibles; una sesión sin trades aparece como retorno exactamente cero.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import math
import textwrap
from dataclasses import dataclass
from math import isfinite
from statistics import NormalDist

from edgelab.stats.cluster_estimand import MIN_STUDENTIZED_SESSIONS

DSR_MIN = 0.95
MIN_DSR_SESSIONS = MIN_STUDENTIZED_SESSIONS
DSR_DEPENDENCE_METHOD = "session_hac_bartlett_v2"

_METHOD_SPEC = {
    "id": DSR_DEPENDENCE_METHOD,
    "observational_unit": "eligible_session_calendar",
    "minimum_sessions": MIN_DSR_SESSIONS,
    "calendar": (
        "complete preregistered eligible-session calendar; no-trade sessions "
        "are exact zero and calendar_sha256 is persisted"
    ),
    "scale": "non_annualized session return with one fixed risk denominator",
    "sharpe": "mean(session_return)/population_sd(session_return)",
    "dependence": "Bartlett HAC long-run variance of centered session returns",
    "lag_default": "ceil(sqrt(n)), bounded to [1,n-1]",
    "effective_n": "max(2,n/max(1,HAC_variance/sample_variance))",
    "negative_dependence": "never permits effective_n above n",
    "multiplicity": "expected maximum Sharpe with preregistered manifest N_eff",
    "tail": "P(SR_observed > expected_max_SR_under_null)",
    "implementation_identity": "separate SHA-256 of canonical Python AST",
}
DSR_METHOD_SHA256_V2 = hashlib.sha256(
    json.dumps(
        _METHOD_SPEC,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

_N = NormalDist()
_EULER = 0.5772156649015329


class DSRCalibrationError(ValueError):
    """La evidencia no representa el método DSR preregistrado."""


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
    sample_variance: float
    hac_variance: float
    dependence_factor: float
    zero_trade_sessions: int
    calendar_sha256: str
    implementation_sha256: str
    dependence_method: str = DSR_DEPENDENCE_METHOD
    method_sha256: str = DSR_METHOD_SHA256_V2


def _number(value, field):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isfinite(value)
    ):
        raise DSRCalibrationError("%s debe ser numérico finito" % field)
    return float(value)


def _sha256(value, field):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdefABCDEF" for character in value)
    ):
        raise DSRCalibrationError("%s debe ser SHA-256 completo" % field)
    return value.lower()


def expected_max_sharpe(n_trials, var_sharpe):
    n_trials = _number(n_trials, "n_trials")
    var_sharpe = _number(var_sharpe, "var_sharpe")
    if n_trials < 1:
        raise DSRCalibrationError("n_trials debe ser >= 1")
    if var_sharpe < 0:
        raise DSRCalibrationError("var_sharpe no puede ser negativa")
    if n_trials < 2:
        return 0.0
    deviation = math.sqrt(var_sharpe)
    first = _N.inv_cdf(1 - 1.0 / n_trials)
    second = _N.inv_cdf(1 - 1.0 / (n_trials * math.e))
    return deviation * ((1 - _EULER) * first + _EULER * second)


def deflated_sharpe(
    sharpe,
    n_obs,
    n_trials,
    *,
    skew=0.0,
    kurtosis=3.0,
    var_sharpe=None,
):
    sharpe = _number(sharpe, "sharpe")
    n_obs = _number(n_obs, "n_obs")
    n_trials = _number(n_trials, "n_trials")
    skew = _number(skew, "skew")
    kurtosis = _number(kurtosis, "kurtosis")
    if n_obs < 2:
        return 0.0
    if n_trials < 1:
        raise DSRCalibrationError("n_trials debe ser >= 1")
    if var_sharpe is None:
        var_sharpe = (
            1 - skew * sharpe + (kurtosis - 1) / 4.0 * sharpe**2
        ) / (n_obs - 1)
    var_sharpe = _number(var_sharpe, "var_sharpe")
    if var_sharpe <= 0:
        raise DSRCalibrationError("var_sharpe debe ser positiva")
    expected = expected_max_sharpe(n_trials, var_sharpe)
    return _N.cdf((sharpe - expected) / math.sqrt(var_sharpe))


def deflated_sharpe_sessions(
    session_returns,
    n_trials,
    hac_lag=None,
    *,
    calendar_sha256=None,
    zero_trade_sessions=None,
):
    """Calcula DSR sobre el calendario completo de sesiones elegibles."""
    values = tuple(_number(value, "session_return") for value in session_returns)
    n = len(values)
    if n < MIN_DSR_SESSIONS:
        raise DSRCalibrationError(
            "DSR formal requiere al menos %d sesiones" % MIN_DSR_SESSIONS
        )
    calendar_sha256 = _sha256(calendar_sha256, "calendar_sha256")
    if (
        not isinstance(zero_trade_sessions, int)
        or isinstance(zero_trade_sessions, bool)
        or not 0 <= zero_trade_sessions <= n
    ):
        raise DSRCalibrationError(
            "zero_trade_sessions debe ser entero entre 0 y n_sessions"
        )
    if zero_trade_sessions > sum(value == 0.0 for value in values):
        raise DSRCalibrationError(
            "cada sesión sin trades debe estar representada por retorno cero"
        )

    mean = sum(values) / n
    centered = tuple(value - mean for value in values)
    sample_variance = sum(value * value for value in centered) / n
    if sample_variance <= 0:
        raise DSRCalibrationError("varianza de sesión no positiva")
    sharpe = mean / math.sqrt(sample_variance)
    third = sum(value**3 for value in centered) / n
    fourth = sum(value**4 for value in centered) / n
    skew = third / sample_variance**1.5
    kurtosis = fourth / sample_variance**2

    if hac_lag is None:
        hac_lag = min(n - 1, max(1, int(math.ceil(math.sqrt(n)))))
    if (
        not isinstance(hac_lag, int)
        or isinstance(hac_lag, bool)
        or not 0 <= hac_lag < n
    ):
        raise DSRCalibrationError("hac_lag debe estar entre 0 y n_sessions-1")

    hac_variance = sample_variance
    for lag in range(1, hac_lag + 1):
        covariance = sum(
            centered[index] * centered[index - lag]
            for index in range(lag, n)
        ) / n
        weight = 1.0 - lag / (hac_lag + 1.0)
        hac_variance += 2.0 * weight * covariance
    if not isfinite(hac_variance) or hac_variance <= 0:
        raise DSRCalibrationError("varianza HAC no positiva o no finita")

    dependence_factor = max(1.0, hac_variance / sample_variance)
    n_effective = max(2.0, n / dependence_factor)
    var_sharpe = (
        1 - skew * sharpe + (kurtosis - 1) / 4.0 * sharpe**2
    ) / (n_effective - 1)
    if not isfinite(var_sharpe) or var_sharpe <= 0:
        raise DSRCalibrationError("varianza del Sharpe no positiva")
    probability = deflated_sharpe(
        sharpe,
        n_effective,
        n_trials,
        skew=skew,
        kurtosis=kurtosis,
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
        sample_variance=sample_variance,
        hac_variance=hac_variance,
        dependence_factor=dependence_factor,
        zero_trade_sessions=zero_trade_sessions,
        calendar_sha256=calendar_sha256,
        implementation_sha256=DSR_IMPLEMENTATION_SHA256,
    )


def _ast_digest(*functions):
    canonical = []
    for function in functions:
        try:
            source = textwrap.dedent(inspect.getsource(function))
        except (OSError, TypeError) as exc:
            raise DSRCalibrationError(
                "no se pudo identificar la implementación DSR"
            ) from exc
        canonical.append(
            ast.dump(
                ast.parse(source),
                annotate_fields=True,
                include_attributes=False,
            )
        )
    return hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest()


DSR_IMPLEMENTATION_SHA256 = _ast_digest(
    expected_max_sharpe,
    deflated_sharpe,
    deflated_sharpe_sessions,
)
