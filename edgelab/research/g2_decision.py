"""Evidencia DSR y decisión G2 persistible, canónica y fail-closed."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite

G2_REQUIRED_GATES=("mcpt","pbo","dsr","walk_forward","parameter_sensitivity")
DSR_MIN=0.95
ESTIMAND_ID="theta_trade=sum_pnl_net/n_trades"
CLUSTER_UNIT="session"
AUTHORIZED_DSR_METHOD_SHA256S=frozenset()


class G2DecisionError(ValueError): pass


def _text(value,field):
    if not isinstance(value,str) or not value.strip():
        raise G2DecisionError("%s debe ser texto no vacio"%field)
    return value


def _sha(value,field):
    _text(value,field)
    if len(value)!=64 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise G2DecisionError("%s debe ser SHA-256 completo"%field)
    return value.lower()


def _utc(value):
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except (TypeError,ValueError) as exc: raise G2DecisionError("created_utc invalido") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds()!=0:
        raise G2DecisionError("created_utc debe declarar UTC")


def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)


def _digest(value): return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class GateResult:
    name:str; passed:bool; value:float; threshold:float; evidence_digest:str; detail:str=""
    def __post_init__(self):
        if self.name not in G2_REQUIRED_GATES: raise G2DecisionError("gate desconocido: %s"%self.name)
        if not isinstance(self.passed,bool): raise G2DecisionError("gate passed debe ser bool")
        for value,field in ((self.value,"value"),(self.threshold,"threshold")):
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value):
                raise G2DecisionError("gate %s debe ser finito"%field)
        _sha(self.evidence_digest,"evidence_digest")


@dataclass(frozen=True)
class DSREvidence:
    probability:float; observational_unit:str; scale:str; n_observations:int
    n_effective:float; n_trials_effective:float; skew:float; kurtosis:float
    dependence_method:str; method_sha256:str
    def __post_init__(self):
        if not isinstance(self.probability,(int,float)) or isinstance(self.probability,bool) or not isfinite(self.probability) or not 0<=self.probability<=1:
            raise G2DecisionError("DSR probability debe estar entre 0 y 1")
        if self.observational_unit!=CLUSTER_UNIT: raise G2DecisionError("DSR observational_unit debe ser session")
        if self.scale!="non_annualized": raise G2DecisionError("DSR scale debe ser non_annualized")
        if not isinstance(self.n_observations,int) or isinstance(self.n_observations,bool) or self.n_observations<2:
            raise G2DecisionError("DSR n_observations debe ser entero >=2")
        for value,field in ((self.n_effective,"n_effective"),(self.n_trials_effective,"n_trials_effective")):
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value) or value<=0:
                raise G2DecisionError("DSR %s debe ser positivo finito"%field)
        if self.n_effective>self.n_observations: raise G2DecisionError("DSR n_effective no puede superar observaciones")
        for value,field in ((self.skew,"skew"),(self.kurtosis,"kurtosis")):
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value):
                raise G2DecisionError("DSR %s debe ser finito"%field)
        _text(self.dependence_method,"dependence_method"); _sha(self.method_sha256,"method_sha256")
    @property
    def passed(self):
        return self.probability>=DSR_MIN and self.method_sha256.lower() in AUTHORIZED_DSR_METHOD_SHA256S
    def gate_result(self):
        authorized=self.method_sha256.lower() in AUTHORIZED_DSR_METHOD_SHA256S
        return GateResult("dsr",self.passed,float(self.probability),DSR_MIN,_digest(asdict(self)),"authorized" if authorized else "dependence method not authorized")


@dataclass(frozen=True)
class PrimaryCI:
    lower:float; upper:float; confidence:float; method:str; n_sessions:int; evidence_digest:str
    def __post_init__(self):
        for value,field in ((self.lower,"lower"),(self.upper,"upper"),(self.confidence,"confidence")):
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value): raise G2DecisionError("primary_ci %s debe ser finito"%field)
        if self.lower>self.upper: raise G2DecisionError("primary_ci lower no puede superar upper")
        if not 0<self.confidence<1: raise G2DecisionError("primary_ci confidence invalido")
        if self.method!="stationary_bootstrap_t": raise G2DecisionError("primary_ci method no autorizado")
        if not isinstance(self.n_sessions,int) or isinstance(self.n_sessions,bool) or self.n_sessions<160: raise G2DecisionError("primary_ci requiere al menos 160 sesiones")
        _sha(self.evidence_digest,"primary_ci evidence_digest")
    @property
    def passed(self): return self.lower>0


@dataclass(frozen=True)
class G2ValidationDecision:
    decision_id:str; campaign_id:str; run_id:str; config_id:str; contract_sha256:str
    estimand_id:str; cluster_unit:str; null_id:str; gate_results:tuple[GateResult,...]
    primary_ci:PrimaryCI; multiplicity_method:str; n_effective:float; created_utc:str
    def __post_init__(self):
        for field in ("decision_id","campaign_id","run_id","config_id","null_id","multiplicity_method"): _text(getattr(self,field),field)
        _sha(self.contract_sha256,"contract_sha256")
        if self.estimand_id!=ESTIMAND_ID: raise G2DecisionError("estimand_id no canonico")
        if self.cluster_unit!=CLUSTER_UNIT: raise G2DecisionError("cluster_unit debe ser session")
        if tuple(x.name for x in self.gate_results)!=G2_REQUIRED_GATES: raise G2DecisionError("gate_results debe coincidir exactamente y en orden")
        if not isinstance(self.n_effective,(int,float)) or isinstance(self.n_effective,bool) or not isfinite(self.n_effective) or self.n_effective<=0 or self.n_effective>self.primary_ci.n_sessions: raise G2DecisionError("n_effective invalido")
        _utc(self.created_utc)
    @property
    def passed(self): return self.primary_ci.passed and all(x.passed for x in self.gate_results)
    @property
    def required_gates(self): return G2_REQUIRED_GATES
    @property
    def evidence_digest(self): return _digest({"gate_results":[asdict(x) for x in self.gate_results],"primary_ci":asdict(self.primary_ci)})
    def to_dict(self):
        value=asdict(self); value["gate"]="G2"; value["required_gates"]=list(G2_REQUIRED_GATES)
        value["gate_results"]={x.name:asdict(x) for x in self.gate_results}
        value["evidence_digest"]=self.evidence_digest; value["passed"]=self.passed
        return value
    @property
    def decision_digest(self): return _digest(self.to_dict())
