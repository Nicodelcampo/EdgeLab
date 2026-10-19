"""Structured proposal intake only; completeness never grants research authority."""
from dataclasses import dataclass,asdict
from .store import ID,digest

@dataclass(frozen=True)
class Draft:
    hypothesis_id: str
    question: str
    mechanism: str
    event_unit: str
    causal_availability: str
    control_definition: str
    outcome_definition: str
    multiplicity_family: str
    validation_plan: str
    falsification_plan: str
    resource_budget: str
    campaign_authority_ref: str
    status: str = 'PROPOSED_UNAUTHORIZED'


def audit_draft(draft):
    data=asdict(draft)
    if not isinstance(draft.hypothesis_id,str) or not ID.fullmatch(draft.hypothesis_id):raise ValueError('invalid hypothesis id')
    if draft.status!='PROPOSED_UNAUTHORIZED':raise ValueError('proposal cannot approve itself')
    for k,v in data.items():
        if k in {'hypothesis_id','status'}:continue
        if not isinstance(v,str) or not 1<=len(v.strip())<=4096:raise ValueError('missing or oversized field: '+k)
    return {'status':'STRUCTURALLY_COMPLETE_NOT_APPROVED','proposal_sha256':digest(data),
            'scientific_validity_verified':False,'authorization_verified':False,
            'outcomes_authorized':False,'holdout_authorized':False,'execution_enabled':False,
            'required_next_reviews':['campaign authority and frozen partitions','causal timing and control validity',
                                     'multiplicity history and statistical design','costs, support and finite resources']}
