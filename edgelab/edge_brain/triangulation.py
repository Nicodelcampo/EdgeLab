"""Dependency-triggered independent confirmation before promotion."""
from dataclasses import dataclass
from typing import Iterable,Mapping,Sequence
from .invalidation import DependencyEdge,HARD_RELATIONS,SOFT_RELATIONS
AXES=frozenset({"instrument","contract","calendar_month_set","measurement_contract_id","kernel","code_commit","model_run_id","effective_backend","effective_model_id","coverage_artifact_id"})
REPRODUCED="REPRODUCED"; NOT_REPRODUCED="NOT_REPRODUCED"; INCONCLUSIVE="INCONCLUSIVE"; CONFIRMED="TRIANGULATION_CONFIRMED"; PENDING="TRIANGULATION_PENDING"; INSUFFICIENT="TRIANGULATION_INSUFFICIENT_INDEPENDENCE"; FAILED="TRIANGULATION_FAILED_PRIOR_NOT_REPRODUCED"; MIXED="TRIANGULATION_CONTRADICTED_MIXED"
@dataclass(frozen=True)
class RunContext:
 axes:Mapping[str,str]
 def __post_init__(self):
  if not self.axes or set(self.axes)-AXES: raise ValueError("invalid/empty independence axes")
 def differs(self,other,axis): return axis in self.axes and axis in other.axes and self.axes[axis]!=other.axes[axis]
@dataclass(frozen=True)
class ConfirmationAttempt:
 attempt_id:str; prior_claim_id:str; context:RunContext; outcome:str; evidence_ids:tuple[str,...]=()
 def __post_init__(self):
  if self.outcome not in {REPRODUCED,NOT_REPRODUCED,INCONCLUSIVE}: raise ValueError("invalid outcome")
  if self.outcome!=INCONCLUSIVE and not self.evidence_ids: raise ValueError("deterministic evidence required")
@dataclass(frozen=True)
class TriangulationPlan:
 dependent_id:str; prior_claim_id:str; relation:str; baseline:RunContext; required_independent_axes:tuple[str,...]; min_confirmations:int=1
@dataclass(frozen=True)
class TriangulationResult:
 plan:TriangulationPlan; verdict:str; accepted_attempt_ids:tuple[str,...]; rejected_attempt_ids:tuple[str,...]; reasons:tuple[str,...]
 @property
 def permits_promotion(self): return self.verdict==CONFIRMED
def plan_triangulation(dependent_id:str,*,edges:Iterable[DependencyEdge],baseline:RunContext,required_independent_axes:Sequence[str]=("contract","measurement_contract_id"),min_confirmations:int=1)->list[TriangulationPlan]:
 out=[]
 for e in edges:
  if e.source_id==dependent_id and e.relation in HARD_RELATIONS|SOFT_RELATIONS: out.append(TriangulationPlan(dependent_id,e.target_id,e.relation,baseline,tuple(required_independent_axes),min_confirmations))
 return sorted(out,key=lambda p:p.prior_claim_id)
def evaluate_triangulation(plan:TriangulationPlan,attempts:Iterable[ConfirmationAttempt])->TriangulationResult:
 accepted=[]; rejected=[]
 for a in attempts:
  if a.prior_claim_id!=plan.prior_claim_id: continue
  if a.outcome==INCONCLUSIVE or not all(a.context.differs(plan.baseline,x) for x in plan.required_independent_axes): rejected.append(a.attempt_id)
  else: accepted.append(a)
 yes=[a for a in accepted if a.outcome==REPRODUCED]; no=[a for a in accepted if a.outcome==NOT_REPRODUCED]
 v=MIXED if yes and no else FAILED if no else CONFIRMED if len(yes)>=plan.min_confirmations else INSUFFICIENT if rejected and not accepted else PENDING
 return TriangulationResult(plan,v,tuple(a.attempt_id for a in accepted),tuple(rejected),(f"{len(yes)} confirmations; {len(no)} refutations.",))
def gate_promotion(results:Sequence[TriangulationResult])->dict:
 blocking=[r.plan.prior_claim_id for r in results if not r.permits_promotion]
 return {"may_promote":bool(results) and not blocking,"blocking_priors":blocking,"reason":"all priors independently confirmed" if results and not blocking else "promotion blocked"}
