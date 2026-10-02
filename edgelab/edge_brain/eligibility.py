"""Fail-closed analysis eligibility gate."""
from dataclasses import dataclass
from typing import Mapping,Sequence
from .coverage import CoverageCell,OBSERVED_SPARSE,EXPECTED_BUT_MISSING,verify_coverage_artifact
ELIGIBLE="ELIGIBLE"; ELIGIBLE_WITH_DECLARED_GAPS="ELIGIBLE_WITH_DECLARED_GAPS"; ABSTAIN_MISSING_CERTIFIED_ROLL="ABSTAIN_MISSING_CERTIFIED_ROLL"; ABSTAIN_MISSING_COVERAGE_ARTIFACT="ABSTAIN_MISSING_COVERAGE_ARTIFACT"; ABSTAIN_INSUFFICIENT_COVERAGE="ABSTAIN_INSUFFICIENT_COVERAGE"; ABSTAIN_UNDECLARED_SCOPE="ABSTAIN_UNDECLARED_SCOPE"
@dataclass(frozen=True)
class AnalysisRequest:
 analysis_id:str; unit_of_analysis:str; requires_continuous_series:bool; requires_certified_roll:bool; eligible_contracts:tuple[str,...]; eligible_months:tuple[str,...]; coverage_artifact_id:str|None; min_observed_cells:int=1; accepts_sparse_cells:bool=False; declared_custody_gaps:bool=False
 def __post_init__(self):
  if self.requires_certified_roll and not self.requires_continuous_series: raise ValueError("certified roll implies continuous series")
  if self.min_observed_cells<1: raise ValueError("min_observed_cells must be positive")
@dataclass(frozen=True)
class EligibilityDecision:
 analysis_id:str; verdict:str; reasons:tuple[str,...]; eligible_cell_keys:tuple[tuple[str,str,str],...]=(); excluded_cell_keys:tuple[tuple[str,str,str],...]=()
 @property
 def may_run(self): return self.verdict in {ELIGIBLE,ELIGIBLE_WITH_DECLARED_GAPS}
def evaluate_eligibility(req:AnalysisRequest,*,coverage_artifact:Mapping|None,cells:Sequence[CoverageCell],certified_roll_ids:Sequence[str]=())->EligibilityDecision:
 if (req.requires_continuous_series or req.requires_certified_roll) and not certified_roll_ids: return EligibilityDecision(req.analysis_id,ABSTAIN_MISSING_CERTIFIED_ROLL,("No certified roll methodology; contract-month slices cannot be concatenated.",))
 if not req.coverage_artifact_id or not coverage_artifact or coverage_artifact.get("coverage_artifact_id")!=req.coverage_artifact_id or not verify_coverage_artifact(coverage_artifact): return EligibilityDecision(req.analysis_id,ABSTAIN_MISSING_COVERAGE_ARTIFACT,("Missing, mismatched, or tampered coverage artifact.",))
 if not req.eligible_contracts or not req.eligible_months: return EligibilityDecision(req.analysis_id,ABSTAIN_UNDECLARED_SCOPE,("eligible_contracts and eligible_months must be explicit.",))
 selected=[c for c in cells if c.contract in req.eligible_contracts and c.calendar_month in req.eligible_months]
 observed=[c for c in selected if c.is_observed and (req.accepts_sparse_cells or c.state!=OBSERVED_SPARSE)]; excluded=[c for c in selected if c not in observed]; gaps=[c for c in selected if c.state==EXPECTED_BUT_MISSING]
 if len(observed)<req.min_observed_cells or (gaps and not req.declared_custody_gaps): return EligibilityDecision(req.analysis_id,ABSTAIN_INSUFFICIENT_COVERAGE,(f"{len(observed)} observed cells; {len(gaps)} custody gaps.",),tuple(c.key for c in observed),tuple(c.key for c in excluded))
 return EligibilityDecision(req.analysis_id,ELIGIBLE_WITH_DECLARED_GAPS if gaps else ELIGIBLE,(f"{len(observed)} observed cells are eligible.",),tuple(c.key for c in observed),tuple(c.key for c in excluded))
