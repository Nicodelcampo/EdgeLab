"""Fail-closed research-saturation and novelty gate for recursive discovery."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
OPEN_NOVEL_EPISODE="OPEN_NOVEL_EPISODE";OPEN_BELOW_SATURATION="OPEN_BELOW_SATURATION";ABSTAIN_RESEARCH_SATURATED="ABSTAIN_RESEARCH_SATURATED";ABSTAIN_INSUFFICIENT_NOVELTY="ABSTAIN_INSUFFICIENT_NOVELTY";ABSTAIN_HOLDOUT_GOVERNANCE="ABSTAIN_HOLDOUT_GOVERNANCE";HARD_NOVELTY=frozenset({"NEW_DATASET","NEW_OBSERVABLE","NEW_EXECUTION_CONTRACT"})
@dataclass(frozen=True)
class CampaignEvidence:
 campaign_id:str;lineage_id:str;dataset_ids:tuple[str,...];observable_fields:tuple[str,...];mechanism_family:str;execution_contract:str;policy_count:int;survivor_count:int;validation_accessed:bool=False;holdout_accessed:bool=False
 def __post_init__(self):
  if self.policy_count<1:raise ValueError("policy_count must be positive")
  if self.survivor_count<0:raise ValueError("survivor_count cannot be negative")
@dataclass(frozen=True)
class CampaignProposal:
 campaign_id:str;lineage_id:str;dataset_ids:tuple[str,...];observable_fields:tuple[str,...];mechanism_family:str;execution_contract:str;requests_validation:bool=False;requests_holdout:bool=False;candidate_lock_present:bool=False;human_holdout_authorization:bool=False
@dataclass(frozen=True)
class ResearchNoveltyDecision:
 campaign_id:str;verdict:str;reasons:tuple[str,...];novel_dimensions:tuple[str,...];cumulative_policy_count:int;zero_survivor_campaigns:int;saturated:bool
 @property
 def may_open(self):return self.verdict in {OPEN_NOVEL_EPISODE,OPEN_BELOW_SATURATION}
def evaluate_research_novelty(proposal:CampaignProposal,history:Sequence[CampaignEvidence],*,saturation_policy_threshold:int=10000,saturation_zero_family_threshold:int=4)->ResearchNoveltyDecision:
 lineage=[x for x in history if x.lineage_id==proposal.lineage_id];policies=sum(x.policy_count for x in lineage);zero=sum(x.survivor_count==0 for x in lineage);saturated=policies>=saturation_policy_threshold and zero>=saturation_zero_family_threshold;datasets={v for x in lineage for v in x.dataset_ids};observables={v for x in lineage for v in x.observable_fields};mechanisms={x.mechanism_family for x in lineage};executions={x.execution_contract for x in lineage};novelty=[]
 if set(proposal.dataset_ids)-datasets:novelty.append("NEW_DATASET")
 if set(proposal.observable_fields)-observables:novelty.append("NEW_OBSERVABLE")
 if proposal.execution_contract not in executions:novelty.append("NEW_EXECUTION_CONTRACT")
 if proposal.mechanism_family not in mechanisms:novelty.append("NEW_MECHANISM")
 if proposal.requests_holdout and not(proposal.candidate_lock_present and proposal.human_holdout_authorization):return ResearchNoveltyDecision(proposal.campaign_id,ABSTAIN_HOLDOUT_GOVERNANCE,("Holdout requires a frozen candidate lock and explicit human authorization.",),tuple(novelty),policies,zero,saturated)
 if proposal.requests_validation and not proposal.candidate_lock_present:return ResearchNoveltyDecision(proposal.campaign_id,ABSTAIN_HOLDOUT_GOVERNANCE,("Validation requires a serialized candidate lock.",),tuple(novelty),policies,zero,saturated)
 if not novelty:return ResearchNoveltyDecision(proposal.campaign_id,ABSTAIN_INSUFFICIENT_NOVELTY,("Proposal repeats dataset, observables, mechanism and execution contract.",),(),policies,zero,saturated)
 if saturated and not(HARD_NOVELTY&set(novelty)):return ResearchNoveltyDecision(proposal.campaign_id,ABSTAIN_RESEARCH_SATURATED,("Lineage is saturated; a new narrative or threshold family is insufficient without new data, observables, or execution evidence.",),tuple(novelty),policies,zero,True)
 return ResearchNoveltyDecision(proposal.campaign_id,OPEN_NOVEL_EPISODE if saturated else OPEN_BELOW_SATURATION,("Proposal introduces admissible hard novelty." if saturated else "Lineage is below saturation threshold.",),tuple(novelty),policies,zero,saturated)
