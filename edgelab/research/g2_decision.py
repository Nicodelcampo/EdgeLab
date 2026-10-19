"""Evidencia DSR y decisión G2 persistible, canónica y fail-closed.

Enmienda G2-A1 (2026-08-10): `mcpt` sale de `G2_REQUIRED_GATES` -- contradecia
estructuralmente a G1 (ver docstring de `edgelab.research.g2` y
`docs/incidents/AMENDMENT_G2-A1_2026-08-10.md`). El bootstrap estacionario-t de
`PrimaryCI` (ya presente acá, `lower > 0`) es el gate que cumple ese rol.
`AUTHORIZED_DSR_METHOD_SHA256S` se puebla con el hash real del método vigente
en vez de quedar vacío -- un allowlist vacío no es conservador, es un candado
sin llave: nunca aprueba nada, con cualquier evidencia."""
from __future__ import annotations
import hashlib,json
from dataclasses import asdict,dataclass
from datetime import datetime
from math import isfinite
from edgelab.research.g2 import dsr_method_sha256
G2_REQUIRED_GATES=("pbo","dsr","walk_forward","parameter_sensitivity")
DSR_MIN=.95; ESTIMAND_ID="theta_trade=sum_pnl_net/n_trades"; CLUSTER_UNIT="session"
AUTHORIZED_DSR_METHOD_SHA256S=frozenset({dsr_method_sha256()})
class G2DecisionError(ValueError): pass
def _text(v,f):
 if not isinstance(v,str) or not v.strip(): raise G2DecisionError(f+" debe ser texto no vacio")
 return v
def _sha(v,f):
 _text(v,f)
 if len(v)!=64 or any(c not in "0123456789abcdefABCDEF" for c in v): raise G2DecisionError(f+" debe ser SHA-256 completo")
 return v.lower()
def _utc(v):
 try: d=datetime.fromisoformat(v.replace("Z","+00:00"))
 except (TypeError,ValueError) as e: raise G2DecisionError("created_utc invalido") from e
 if d.tzinfo is None or d.utcoffset() is None or d.utcoffset().total_seconds()!=0: raise G2DecisionError("created_utc debe declarar UTC")
def _canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
def _digest(v): return hashlib.sha256(_canonical(v).encode()).hexdigest()
@dataclass(frozen=True)
class GateResult:
 name:str; passed:bool; value:float; threshold:float; evidence_digest:str; detail:str=""
 def __post_init__(self):
  if self.name not in G2_REQUIRED_GATES: raise G2DecisionError("gate desconocido: "+self.name)
  if not isinstance(self.passed,bool): raise G2DecisionError("gate passed debe ser bool")
  for v,f in ((self.value,"value"),(self.threshold,"threshold")):
   if not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v): raise G2DecisionError("gate "+f+" debe ser finito")
  _sha(self.evidence_digest,"evidence_digest")
@dataclass(frozen=True)
class DSREvidence:
 probability:float; observational_unit:str; scale:str; n_observations:int; n_effective:float; n_trials_effective:float; skew:float; kurtosis:float; dependence_method:str; method_sha256:str
 def __post_init__(self):
  if not isinstance(self.probability,(int,float)) or isinstance(self.probability,bool) or not isfinite(self.probability) or not 0<=self.probability<=1: raise G2DecisionError("DSR probability debe estar entre 0 y 1")
  if self.observational_unit!=CLUSTER_UNIT: raise G2DecisionError("DSR observational_unit debe ser session")
  if self.scale!="non_annualized": raise G2DecisionError("DSR scale debe ser non_annualized")
  if not isinstance(self.n_observations,int) or isinstance(self.n_observations,bool) or self.n_observations<2: raise G2DecisionError("DSR n_observations debe ser entero >=2")
  for v,f in ((self.n_effective,"n_effective"),(self.n_trials_effective,"n_trials_effective")):
   if not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v) or v<=0: raise G2DecisionError("DSR "+f+" debe ser positivo finito")
  if self.n_effective>self.n_observations: raise G2DecisionError("DSR n_effective no puede superar observaciones")
  for v,f in ((self.skew,"skew"),(self.kurtosis,"kurtosis")):
   if not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v): raise G2DecisionError("DSR "+f+" debe ser finito")
  _text(self.dependence_method,"dependence_method"); _sha(self.method_sha256,"method_sha256")
 @property
 def passed(self): return self.probability>=DSR_MIN and self.method_sha256.lower() in AUTHORIZED_DSR_METHOD_SHA256S
 def gate_result(self):
  a=self.method_sha256.lower() in AUTHORIZED_DSR_METHOD_SHA256S
  return GateResult("dsr",self.passed,float(self.probability),DSR_MIN,_digest(asdict(self)),"authorized" if a else "dependence method not authorized")
@dataclass(frozen=True)
class PrimaryCI:
 lower:float; upper:float; confidence:float; method:str; n_sessions:int; evidence_digest:str
 def __post_init__(self):
  for v,f in ((self.lower,"lower"),(self.upper,"upper"),(self.confidence,"confidence")):
   if not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v): raise G2DecisionError("primary_ci "+f+" debe ser finito")
  if self.lower>self.upper: raise G2DecisionError("primary_ci lower no puede superar upper")
  if not 0<self.confidence<1: raise G2DecisionError("primary_ci confidence invalido")
  if self.method!="stationary_bootstrap_t": raise G2DecisionError("primary_ci method no autorizado")
  if not isinstance(self.n_sessions,int) or isinstance(self.n_sessions,bool) or self.n_sessions<160: raise G2DecisionError("primary_ci requiere al menos 160 sesiones")
  _sha(self.evidence_digest,"primary_ci evidence_digest")
 @property
 def passed(self): return self.lower>0
@dataclass(frozen=True)
class G2ValidationDecision:
 decision_id:str; campaign_id:str; run_id:str; config_id:str; contract_sha256:str; estimand_id:str; cluster_unit:str; null_id:str; gate_results:tuple[GateResult,...]; primary_ci:PrimaryCI; multiplicity_method:str; n_effective:float; created_utc:str
 def __post_init__(self):
  for f in ("decision_id","campaign_id","run_id","config_id","null_id","multiplicity_method"): _text(getattr(self,f),f)
  _sha(self.contract_sha256,"contract_sha256")
  if self.estimand_id!=ESTIMAND_ID: raise G2DecisionError("estimand_id no canonico")
  if self.cluster_unit!=CLUSTER_UNIT: raise G2DecisionError("cluster_unit debe ser session")
  if tuple(x.name for x in self.gate_results)!=G2_REQUIRED_GATES: raise G2DecisionError("gate_results debe coincidir exactamente y en orden")
  if not isinstance(self.n_effective,(int,float)) or isinstance(self.n_effective,bool) or not isfinite(self.n_effective) or self.n_effective<=0 or self.n_effective>self.primary_ci.n_sessions: raise G2DecisionError("n_effective invalido")
  _utc(self.created_utc)
 @property
 def passed(self): return self.primary_ci.passed and all(x.passed for x in self.gate_results)
 @property
 def evidence_digest(self): return _digest({"gate_results":[asdict(x) for x in self.gate_results],"primary_ci":asdict(self.primary_ci)})
 def to_dict(self):
  v=asdict(self); v.update(gate="G2",required_gates=list(G2_REQUIRED_GATES),gate_results={x.name:asdict(x) for x in self.gate_results},evidence_digest=self.evidence_digest,passed=self.passed); return v
 @property
 def decision_digest(self): return _digest(self.to_dict())
def validate_decision_dict(value):
 if not isinstance(value,dict): raise G2DecisionError("validation_decision debe ser objeto")
 if value.get("gate")!="G2": raise G2DecisionError("validation_decision gate debe ser G2")
 if value.get("required_gates")!=list(G2_REQUIRED_GATES): raise G2DecisionError("required_gates no coincide con G2")
 raw=value.get("gate_results")
 if not isinstance(raw,dict) or set(raw)!=set(G2_REQUIRED_GATES): raise G2DecisionError("gate_results no coincide con G2")
 try:
  gates=tuple(GateResult(**raw[n]) for n in G2_REQUIRED_GATES); ci=PrimaryCI(**value["primary_ci"])
  rebuilt=G2ValidationDecision(value["decision_id"],value["campaign_id"],value["run_id"],value["config_id"],value["contract_sha256"],value["estimand_id"],value["cluster_unit"],value["null_id"],gates,ci,value["multiplicity_method"],value["n_effective"],value["created_utc"])
 except (KeyError,TypeError) as e: raise G2DecisionError("validation_decision incompleta o mal formada") from e
 if value.get("passed") is not rebuilt.passed: raise G2DecisionError("passed no coincide con la decisión calculada")
 if value.get("evidence_digest")!=rebuilt.evidence_digest: raise G2DecisionError("evidence_digest no coincide")
 return rebuilt
