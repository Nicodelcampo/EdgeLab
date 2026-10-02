"""Immutable coverage mask. Missing observations are never zero activity."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import re
from typing import Iterable, Mapping
from .registry import content_sha256
OBSERVED="OBSERVED"; OBSERVED_PARTIAL="OBSERVED_PARTIAL"; OBSERVED_SPARSE="OBSERVED_SPARSE"
NOT_OBSERVED="NOT_OBSERVED"; EXPECTED_BUT_MISSING="EXPECTED_BUT_MISSING"; NOT_ELIGIBLE="NOT_ELIGIBLE"
COVERAGE_STATES=frozenset({OBSERVED,OBSERVED_PARTIAL,OBSERVED_SPARSE,NOT_OBSERVED,EXPECTED_BUT_MISSING,NOT_ELIGIBLE})
OBSERVED_STATES=frozenset({OBSERVED,OBSERVED_PARTIAL,OBSERVED_SPARSE}); UNOBSERVED_STATES=frozenset({NOT_OBSERVED,EXPECTED_BUT_MISSING}); SCHEMA_VERSION="1.0.0"
class ZeroFillViolation(ValueError): pass
@dataclass(frozen=True)
class CoverageCell:
 instrument:str; contract:str; calendar_month:str; state:str; observed_active_minutes:int|None=None; expected_active_minutes:int|None=None; evidence_ref:str|None=None
 def __post_init__(self):
  if self.state not in COVERAGE_STATES: raise ValueError(f"invalid coverage state: {self.state}")
  if not re.fullmatch(r"\d{4}-\d{2}",self.calendar_month): raise ValueError("calendar_month must be YYYY-MM")
  if self.expected_active_minutes is not None and self.expected_active_minutes<0: raise ValueError("negative expected minutes")
  if self.state in OBSERVED_STATES:
   if not isinstance(self.observed_active_minutes,int) or self.observed_active_minutes<0: raise ValueError("observed state requires nonnegative integer minutes")
   if not self.evidence_ref: raise ValueError("observed state requires evidence_ref")
  elif self.observed_active_minutes is not None: raise ZeroFillViolation("unobserved/not-eligible cells must use null, never zero")
 @property
 def key(self): return (self.instrument,self.contract,self.calendar_month)
 @property
 def is_observed(self): return self.state in OBSERVED_STATES
def classify_observed_month(observed:int,expected:int,*,tolerance_minutes:int=60,sparse_ratio:float=.10)->str:
 if observed<0 or expected<=0: raise ValueError("invalid minute counts")
 if observed<expected*sparse_ratio:return OBSERVED_SPARSE
 if observed<max(0,expected-tolerance_minutes):return OBSERVED_PARTIAL
 return OBSERVED
def build_coverage_mask(*,universe:Iterable[tuple[str,str,str]],observations:Mapping[tuple[str,str,str],Mapping],expected:Mapping[tuple[str,str,str],int],not_eligible:Iterable[tuple[str,str,str]]=())->list[CoverageCell]:
 excluded=set(not_eligible); cells=[]
 for key in sorted(set(universe)|set(observations)|set(expected)|excluded):
  i,c,m=key
  if key in excluded: cells.append(CoverageCell(i,c,m,NOT_ELIGIBLE)); continue
  if key in observations:
   o=observations[key]; mins=int(o["observed_active_minutes"]); exp=int(expected.get(key,o.get("expected_active_minutes",0)))
   cells.append(CoverageCell(i,c,m,classify_observed_month(mins,exp),mins,exp,str(o["evidence_ref"])))
  elif key in expected: cells.append(CoverageCell(i,c,m,EXPECTED_BUT_MISSING,None,int(expected[key])))
  else: cells.append(CoverageCell(i,c,m,NOT_OBSERVED))
 return cells
def assert_not_zero_fill(state:str,value):
 if state in UNOBSERVED_STATES and value is not None: raise ZeroFillViolation(f"{state} cannot materialize {value!r}; NOT_OBSERVED != ZERO_ACTIVITY")
def active_denominator(cells:Iterable[CoverageCell],*,acknowledge_expected_missing:bool=False)->int:
 cells=list(cells)
 if any(c.state==EXPECTED_BUT_MISSING for c in cells) and not acknowledge_expected_missing: raise ZeroFillViolation("EXPECTED_BUT_MISSING requires explicit acknowledgement")
 return sum(c.is_observed for c in cells)
def to_series(cells:Iterable[CoverageCell])->dict[tuple[str,str,str],int|None]:
 out={}
 for c in cells: assert_not_zero_fill(c.state,c.observed_active_minutes); out[c.key]=c.observed_active_minutes
 return out
def build_coverage_artifact(cells:Iterable[CoverageCell],*,created_at_utc:str,holdout_boundary_ns:int,code_commit:str)->dict:
 cs=sorted((asdict(c) for c in cells),key=lambda x:(x["instrument"],x["contract"],x["calendar_month"]))
 payload={"schema_version":SCHEMA_VERSION,"created_at_utc":created_at_utc,"holdout_boundary_ns":holdout_boundary_ns,"code_commit":code_commit,"invariants":["NOT_OBSERVED != ZERO_ACTIVITY","missing periods are excluded from denominators unless explicitly acknowledged"],"cells":cs,"state_counts":{s:sum(c["state"]==s for c in cs) for s in sorted(COVERAGE_STATES)}}
 return {"coverage_artifact_id":"COV-"+content_sha256(payload)[:16],**payload}
def verify_coverage_artifact(a:Mapping)->bool:
 payload={k:v for k,v in a.items() if k!="coverage_artifact_id"}; return a.get("coverage_artifact_id")=="COV-"+content_sha256(payload)[:16]
