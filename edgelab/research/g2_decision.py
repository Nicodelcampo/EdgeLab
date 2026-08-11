"""Decisión G2 persistible, canónica y fail-closed.

G2-A1 endurecida: el nulo es específico de campaña; DSR consume el calendario
completo de sesiones mediante ``session_hac_bartlett_v2``; DSR e IC primario
comparten población; ningún booleano recibido decide por sí solo.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite

from edgelab.research.g2_dsr import (
    DSR_DEPENDENCE_METHOD,
    DSR_IMPLEMENTATION_SHA256,
    DSR_METHOD_SHA256_V2,
    DSR_MIN,
    MIN_DSR_SESSIONS,
)
from edgelab.research.g2_protocol import CAMPAIGN_NULL_MAX_P
from edgelab.research.g2_ratio import PBO_MAX

G2_REQUIRED_GATES = (
    "campaign_null",
    "pbo",
    "dsr",
    "walk_forward",
    "parameter_sensitivity",
)
ESTIMAND_ID = "theta_trade=sum_pnl_net/n_trades"
CLUSTER_UNIT = "session"
MULTIPLICITY_METHOD = "dsr_manifest_n_eff"
AUTHORIZED_DSR_METHOD_SHA256S = frozenset({DSR_METHOD_SHA256_V2})
AUTHORIZED_DSR_IMPLEMENTATION_SHA256S = frozenset({DSR_IMPLEMENTATION_SHA256})

_GATE_SEMANTICS = {
    "campaign_null": ("le", CAMPAIGN_NULL_MAX_P),
    "pbo": ("le", PBO_MAX),
    "dsr": ("ge", DSR_MIN),
    "walk_forward": ("gt", 0.0),
    "parameter_sensitivity": ("gt", 0.0),
}


class G2DecisionError(ValueError):
    pass


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise G2DecisionError(field + " debe ser texto no vacío")
    return value


def _sha(value, field):
    _text(value, field)
    if len(value) != 64 or any(
        character not in "0123456789abcdefABCDEF" for character in value
    ):
        raise G2DecisionError(field + " debe ser SHA-256 completo")
    return value.lower()


def _number(value, field):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isfinite(value)
    ):
        raise G2DecisionError(field + " debe ser numérico finito")
    return float(value)


def _utc(value):
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise G2DecisionError("created_utc inválido") from exc
    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
        or timestamp.utcoffset().total_seconds() != 0
    ):
        raise G2DecisionError("created_utc debe declarar UTC")


def _canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _gate_passes(name, value, threshold):
    direction, canonical_threshold = _GATE_SEMANTICS[name]
    if threshold != canonical_threshold:
        raise G2DecisionError(
            "gate %s threshold no canónico: %r" % (name, threshold)
        )
    if direction == "le":
        return value <= threshold
    if direction == "ge":
        return value >= threshold
    return value > threshold


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    value: float
    threshold: float
    evidence_digest: str
    detail: str = ""

    def __post_init__(self):
        if self.name not in G2_REQUIRED_GATES:
            raise G2DecisionError("gate desconocido: " + self.name)
        if not isinstance(self.passed, bool):
            raise G2DecisionError("gate passed debe ser bool")
        value = _number(self.value, "gate value")
        threshold = _number(self.threshold, "gate threshold")
        expected = _gate_passes(self.name, value, threshold)
        if self.passed is not expected:
            raise G2DecisionError(
                "gate %s passed no coincide con value/threshold" % self.name
            )
        _sha(self.evidence_digest, "evidence_digest")


@dataclass(frozen=True)
class DSREvidence:
    probability: float
    sharpe: float
    observational_unit: str
    scale: str
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
    dependence_method: str
    method_sha256: str
    implementation_sha256: str

    def __post_init__(self):
        probability = _number(self.probability, "DSR probability")
        if not 0 <= probability <= 1:
            raise G2DecisionError("DSR probability debe estar entre 0 y 1")
        _number(self.sharpe, "DSR sharpe")
        if self.observational_unit != "eligible_session_calendar":
            raise G2DecisionError(
                "DSR observational_unit debe ser eligible_session_calendar"
            )
        if self.scale != "non_annualized":
            raise G2DecisionError("DSR scale debe ser non_annualized")
        if (
            not isinstance(self.n_observations, int)
            or isinstance(self.n_observations, bool)
            or self.n_observations < MIN_DSR_SESSIONS
        ):
            raise G2DecisionError(
                "DSR requiere al menos %d sesiones" % MIN_DSR_SESSIONS
            )
        n_effective = _number(self.n_effective, "DSR n_effective")
        n_trials = _number(self.n_trials_effective, "DSR n_trials_effective")
        if not 2 <= n_effective <= self.n_observations:
            raise G2DecisionError("DSR n_effective fuera de rango")
        if n_trials < 1:
            raise G2DecisionError("DSR n_trials_effective debe ser >=1")
        _number(self.skew, "DSR skew")
        _number(self.kurtosis, "DSR kurtosis")
        if (
            not isinstance(self.hac_lag, int)
            or isinstance(self.hac_lag, bool)
            or not 0 <= self.hac_lag < self.n_observations
        ):
            raise G2DecisionError("DSR hac_lag fuera de rango")
        sample = _number(self.sample_variance, "DSR sample_variance")
        hac = _number(self.hac_variance, "DSR hac_variance")
        factor = _number(self.dependence_factor, "DSR dependence_factor")
        if sample <= 0 or hac <= 0 or factor < 1:
            raise G2DecisionError("DSR varianzas/factor de dependencia inválidos")
        expected_factor = max(1.0, hac / sample)
        expected_n = max(2.0, self.n_observations / expected_factor)
        if not math.isclose(factor, expected_factor, rel_tol=1e-12, abs_tol=1e-12):
            raise G2DecisionError("DSR dependence_factor inconsistente")
        if not math.isclose(n_effective, expected_n, rel_tol=1e-12, abs_tol=1e-12):
            raise G2DecisionError("DSR n_effective inconsistente")
        if (
            not isinstance(self.zero_trade_sessions, int)
            or isinstance(self.zero_trade_sessions, bool)
            or not 0 <= self.zero_trade_sessions <= self.n_observations
        ):
            raise G2DecisionError("DSR zero_trade_sessions inválido")
        _sha(self.calendar_sha256, "DSR calendar_sha256")
        if self.dependence_method != DSR_DEPENDENCE_METHOD:
            raise G2DecisionError("DSR dependence_method no canónico")
        method = _sha(self.method_sha256, "DSR method_sha256")
        implementation = _sha(
            self.implementation_sha256,
            "DSR implementation_sha256",
        )
        if method not in AUTHORIZED_DSR_METHOD_SHA256S:
            raise G2DecisionError("DSR method_sha256 no autorizado")
        if implementation not in AUTHORIZED_DSR_IMPLEMENTATION_SHA256S:
            raise G2DecisionError("DSR implementation_sha256 no autorizado")

    @property
    def passed(self):
        return self.probability >= DSR_MIN

    def gate_result(self):
        return GateResult(
            "dsr",
            self.passed,
            float(self.probability),
            DSR_MIN,
            _digest(asdict(self)),
            "spec and implementation authorized",
        )


@dataclass(frozen=True)
class PrimaryCI:
    lower: float
    upper: float
    confidence: float
    method: str
    n_sessions: int
    calendar_sha256: str
    evidence_digest: str

    def __post_init__(self):
        lower = _number(self.lower, "primary_ci lower")
        upper = _number(self.upper, "primary_ci upper")
        confidence = _number(self.confidence, "primary_ci confidence")
        if lower > upper:
            raise G2DecisionError("primary_ci lower no puede superar upper")
        if not 0 < confidence < 1:
            raise G2DecisionError("primary_ci confidence inválido")
        if self.method != "stationary_bootstrap_t":
            raise G2DecisionError("primary_ci method no autorizado")
        if (
            not isinstance(self.n_sessions, int)
            or isinstance(self.n_sessions, bool)
            or self.n_sessions < MIN_DSR_SESSIONS
        ):
            raise G2DecisionError(
                "primary_ci requiere al menos %d sesiones" % MIN_DSR_SESSIONS
            )
        _sha(self.calendar_sha256, "primary_ci calendar_sha256")
        _sha(self.evidence_digest, "primary_ci evidence_digest")

    @property
    def passed(self):
        return self.lower > 0


@dataclass(frozen=True)
class G2ValidationDecision:
    decision_id: str
    campaign_id: str
    run_id: str
    config_id: str
    contract_sha256: str
    estimand_id: str
    cluster_unit: str
    null_id: str
    gate_results: tuple[GateResult, ...]
    dsr_evidence: DSREvidence
    primary_ci: PrimaryCI
    multiplicity_method: str
    n_effective: float
    created_utc: str

    def __post_init__(self):
        for field in (
            "decision_id",
            "campaign_id",
            "run_id",
            "config_id",
            "null_id",
        ):
            _text(getattr(self, field), field)
        _sha(self.contract_sha256, "contract_sha256")
        if self.estimand_id != ESTIMAND_ID:
            raise G2DecisionError("estimand_id no canónico")
        if self.cluster_unit != CLUSTER_UNIT:
            raise G2DecisionError("cluster_unit debe ser session")
        if tuple(gate.name for gate in self.gate_results) != G2_REQUIRED_GATES:
            raise G2DecisionError(
                "gate_results debe coincidir exactamente y en orden"
            )
        if self.gate_results[2] != self.dsr_evidence.gate_result():
            raise G2DecisionError("gate dsr no coincide con DSREvidence")
        if self.primary_ci.n_sessions != self.dsr_evidence.n_observations:
            raise G2DecisionError("DSR e IC deben usar las mismas sesiones")
        if (
            self.primary_ci.calendar_sha256.lower()
            != self.dsr_evidence.calendar_sha256.lower()
        ):
            raise G2DecisionError("DSR e IC deben usar el mismo calendario")
        if self.multiplicity_method != MULTIPLICITY_METHOD:
            raise G2DecisionError("multiplicity_method no canónico")
        n_effective = _number(self.n_effective, "n_effective")
        if not math.isclose(
            n_effective,
            self.dsr_evidence.n_trials_effective,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise G2DecisionError(
                "n_effective debe coincidir con DSR n_trials_effective"
            )
        _utc(self.created_utc)

    @property
    def passed(self):
        return (
            self.primary_ci.passed
            and self.dsr_evidence.passed
            and all(gate.passed for gate in self.gate_results)
        )

    @property
    def evidence_digest(self):
        return _digest(
            {
                "gate_results": [asdict(gate) for gate in self.gate_results],
                "dsr_evidence": asdict(self.dsr_evidence),
                "primary_ci": asdict(self.primary_ci),
            }
        )

    def to_dict(self):
        value = asdict(self)
        value.update(
            gate="G2",
            required_gates=list(G2_REQUIRED_GATES),
            gate_results={gate.name: asdict(gate) for gate in self.gate_results},
            evidence_digest=self.evidence_digest,
            passed=self.passed,
        )
        return value

    @property
    def decision_digest(self):
        return _digest(self.to_dict())


def validate_decision_dict(value):
    if not isinstance(value, dict):
        raise G2DecisionError("validation_decision debe ser objeto")
    if value.get("gate") != "G2":
        raise G2DecisionError("validation_decision gate debe ser G2")
    if value.get("required_gates") != list(G2_REQUIRED_GATES):
        raise G2DecisionError("required_gates no coincide con G2")
    raw_gates = value.get("gate_results")
    if not isinstance(raw_gates, dict) or set(raw_gates) != set(G2_REQUIRED_GATES):
        raise G2DecisionError("gate_results no coincide con G2")
    try:
        gates = tuple(GateResult(**raw_gates[name]) for name in G2_REQUIRED_GATES)
        dsr_evidence = DSREvidence(**value["dsr_evidence"])
        primary_ci = PrimaryCI(**value["primary_ci"])
        rebuilt = G2ValidationDecision(
            decision_id=value["decision_id"],
            campaign_id=value["campaign_id"],
            run_id=value["run_id"],
            config_id=value["config_id"],
            contract_sha256=value["contract_sha256"],
            estimand_id=value["estimand_id"],
            cluster_unit=value["cluster_unit"],
            null_id=value["null_id"],
            gate_results=gates,
            dsr_evidence=dsr_evidence,
            primary_ci=primary_ci,
            multiplicity_method=value["multiplicity_method"],
            n_effective=value["n_effective"],
            created_utc=value["created_utc"],
        )
    except (KeyError, TypeError) as exc:
        raise G2DecisionError(
            "validation_decision incompleta o mal formada"
        ) from exc
    if value.get("passed") is not rebuilt.passed:
        raise G2DecisionError("passed no coincide con la decisión calculada")
    if value.get("evidence_digest") != rebuilt.evidence_digest:
        raise G2DecisionError("evidence_digest no coincide")
    return rebuilt
