from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any
@dataclass(frozen=True)
class HypothesisProposal:
    hypothesis_id:str; family_id:str; economic_story:str; location:dict[str,Any]; regime:dict[str,Any]; trigger:dict[str,Any]; invalidate:dict[str,Any]; ablations:tuple[str,...]; data_requirements:tuple[str,...]; n_free_params:int; asserts_edge:bool=False; source_type:str="LLM_PROPOSAL"
    def __post_init__(self):
        if self.asserts_edge:raise ValueError("proposal cannot assert edge")
        if self.source_type=="LLM_PROPOSAL" and self.n_free_params>3:raise ValueError("LLM proposal exceeds 3 free parameters")
        if len(self.economic_story.strip())<20:raise ValueError("economic mechanism required")
        if not self.ablations:raise ValueError("at least one ablation required")
    def record(self):return {**asdict(self),"status":"PROPOSED","is_proposal_not_evidence":True}
