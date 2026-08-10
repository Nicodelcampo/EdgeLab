"""Decisión G2 persistible, canónica y fail-closed bajo G2-A1."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite

from edgelab.research.g2 import (
    DSR_DEPENDENCE_METHOD,
    DSR_METHOD_SHA256_V1,
    DSR_MIN,
    MCPT_MAX_P,
    PBO_MAX,
    SessionDSRResult,
)

G2_REQUIRED_GATES = (
    "mcpt",  # nombre estructural histórico; ahora significa nulo de campaña
    "pbo",
    "dsr",
    "walk_forward",
    "parameter_sensitivity",
)
ESTIMAND_ID = "theta_trade=sum_pnl_net/n_trades"
CLUSTER_UNIT = "session"
MULTIPLICITY_METHOD = "dsr_manifest_n_eff"
AUTHORIZED_DSR_METHOD_SHA256S = frozenset({DSR_METHOD_SHA256_V1})
_GATE_THRESHOLDS = {
    "mcpt": MCPT_MAX_P,
    "pbo": PBO_MAX,
    "dsr": DSR_MIN,
    "walk_forward": 0.0,
    "parameter_sensitivity": 0.0,
}


class G2DecisionError(ValueError):
    """La evidencia no permite reconstruir una decisión G2 canónica."""


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


def _utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise G2DecisionError("created_utc inválido") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.utcoffset().total_seconds() != 0
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


def _finite(value, field):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isfinite(value)
    ):
        raise G2DecisionError(field + " debe ser finito")
    return float(value)


def _numeric_gate_passes(name, value):
    threshold = _GATE_THRESHOLDS[name]
    if name in ("mcpt", "pbo"):
        return value <= threshold
    if name == "dsr":
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
        value = _finite(self.value, "gate value")
        threshold = _finite(self.threshold, "gate threshold")
        if threshold != _GATE_THRESHOLDS[self.name]:
            raise G2DecisionError("umbral no canónico para gate " + self.name)
        if self.passed and not _numeric_gate_passes(self.name, value):
            raise G2DecisionError("gate no puede aprobar con ese valor")
        if not self.passed and _numeric_gate_passes(self.name, value) and not self.detail:
            raise G2DecisionError("gate numéricamente verde requiere motivo de veto")
        _sha(self.evidence_digest, "evidence_digest")
        if not isinstance(self.detail, str):
            raise G2DecisionError("gate detail debe ser texto")


@dataclass(frozen=True)
class DSREvidence:
    probability: float
    observational_unit: str
    scale: str
    n_observations: int
    n_effective: float
    n_trials_effective: float
    skew: float
    kurtosis: float
    dependence_method: str
    method_sha256: str

    def __post_init__(self):
        probability = _finite(self.probability, "DSR probability")
        if not 0 <= probability <= 1:
            raise G2DecisionError("DSR probability debe estar entre 0 y 1")
        if self.observational_unit != CLUSTER_UNIT:
            raise G2DecisionError("DSR observational_unit debe ser session")
        if self.scale != "non_annualized":
            raise G2DecisionError("DSR scale debe ser non_annualized")
        if (
            not isinstance(self.n_observations, int)
            or isinstance(self.n_observations, bool)
            or self.n_observations < 3
        ):
            raise G2DecisionError("DSR n_observations debe ser entero >=3")
        n_effective = _finite(self.n_effective, "DSR n_effective")
        n_trials = _finite(self.n_trials_effective, "DSR n_trials_effective")
        if n_effective < 2 or n_effective > self.n_observations:
            raise G2DecisionError("DSR n_effective fuera de rango")
        if n_trials < 1:
            raise G2DecisionError("DSR n_trials_effective debe ser >=1")
        _finite(self.skew, "DSR skew")
        _finite(self.kurtosis, "DSR kurtosis")
        _text(self.dependence_method, "dependence_method")
        _sha(self.method_sha256, "method_sha256")

    @classmethod
    def from_session_result(cls, result: SessionDSRResult):
        if not isinstance(result, SessionDSRResult):
            raise G2DecisionError("result debe ser SessionDSRResult")
        return cls(
            probability=result.probability,
            observational_unit=CLUSTER_UNIT,
            scale="non_annualized",
            n_observations=result.n_observations,
            n_effective=result.n_effective,
            n_trials_effective=result.n_trials_effective,
            skew=result.skew,
            kurtosis=result.kurtosis,
            dependence_method=result.dependence_method,
            method_sha256=result.method_sha256,
        )

    @property
    def method_authorized(self):
        return (
            self.dependence_method == DSR_DEPENDENCE_METHOD
            and self.method_sha256.lower() in AUTHORIZED_DSR_METHOD_SHA256S
        )

    @property
    def passed(self):
        return self.probability >= DSR_MIN and self.method_authorized

    def gate_result(self):
        return GateResult(
            "dsr",
            self.passed,
            float(self.probability),
            DSR_MIN,
            _digest(asdict(self)),
            "authorized" if self.method_authorized else "dependence method not authorized",
        )


@dataclass(frozen=True)
class PrimaryCI:
    lower: float
    upper: float
    confidence: float
    method: str
    n_sessions: int
    evidence_digest: str

    def __post_init__(self):
        lower = _finite(self.lower, "primary_ci lower")
        upper = _finite(self.upper, "primary_ci upper")
        confidence = _finite(self.confidence, "primary_ci confidence")
        if lower > upper:
            raise G2DecisionError("primary_ci lower no puede superar upper")
        if not 0 < confidence < 1:
            raise G2DecisionError("primary_ci confidence inválido")
        if self.method != "stationary_bootstrap_t":
            raise G2DecisionError("primary_ci method no autorizado")
        if (
            not isinstance(self.n_sessions, int)
            or isinstance(self.n_sessions, bool)
            or self.n_sessions < 160
        ):
            raise G2DecisionError("primary_ci requiere al menos 160 sesiones")
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
    primary_ci: PrimaryCI
    dsr_evidence: DSREvidence
    multiplicity_method: str
    n_effective: float
    created_utc: str

    def __post_init__(self):
        for field in ("decision_id", "campaign_id", "run_id", "config_id", "null_id"):
            _text(getattr(self, field), field)
        _sha(self.contract_sha256, "contract_sha256")
        if self.estimand_id != ESTIMAND_ID:
            raise G2DecisionError("estimand_id no canónico")
        if self.cluster_unit != CLUSTER_UNIT:
            raise G2DecisionError("cluster_unit debe ser session")
        if self.multiplicity_method != MULTIPLICITY_METHOD:
            raise G2DecisionError("multiplicity_method no canónico")
        if tuple(result.name for result in self.gate_results) != G2_REQUIRED_GATES:
            raise G2DecisionError("gate_results debe coincidir exactamente y en orden")
        expected_dsr = self.dsr_evidence.gate_result()
        actual_dsr = self.gate_results[G2_REQUIRED_GATES.index("dsr")]
        if actual_dsr != expected_dsr:
            raise G2DecisionError("gate dsr no coincide con DSREvidence embebida")
        if self.dsr_evidence.n_observations != self.primary_ci.n_sessions:
            raise G2DecisionError("DSR e IC primario deben usar las mismas sesiones")
        n_effective = _finite(self.n_effective, "n_effective")
        if n_effective != self.dsr_evidence.n_effective:
            raise G2DecisionError("n_effective no coincide con DSREvidence")
        _utc(self.created_utc)

    @property
    def passed(self):
        return self.primary_ci.passed and all(result.passed for result in self.gate_results)

    @property
    def evidence_digest(self):
        return _digest(
            {
                "gate_results": [asdict(result) for result in self.gate_results],
                "primary_ci": asdict(self.primary_ci),
                "dsr_evidence": asdict(self.dsr_evidence),
            }
        )

    def to_dict(self):
        value = asdict(self)
        value.update(
            gate="G2",
            required_gates=list(G2_REQUIRED_GATES),
            gate_results={result.name: asdict(result) for result in self.gate_results},
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
        primary_ci = PrimaryCI(**value["primary_ci"])
        dsr_evidence = DSREvidence(**value["dsr_evidence"])
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
            primary_ci=primary_ci,
            dsr_evidence=dsr_evidence,
            multiplicity_method=value["multiplicity_method"],
            n_effective=value["n_effective"],
            created_utc=value["created_utc"],
        )
    except (KeyError, TypeError) as exc:
        raise G2DecisionError("validation_decision incompleta o mal formada") from exc
    if value.get("passed") is not rebuilt.passed:
        raise G2DecisionError("passed no coincide con la decisión calculada")
    if value.get("evidence_digest") != rebuilt.evidence_digest:
        raise G2DecisionError("evidence_digest no coincide")
    return rebuilt
