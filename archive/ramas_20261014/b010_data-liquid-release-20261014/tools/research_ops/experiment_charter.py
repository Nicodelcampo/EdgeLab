"""Bounded information-per-cost design gate, never a market execution permit.
Rubric, not calibrated information gain/probability of edge. References point to
canonical knowledge/attempt history; this module creates no scientific memory.
"""
from dataclasses import dataclass, asdict
from datetime import date
from .post_run import _id, _sha
from .knowledge import learning_handoff
from .store import digest

NOVELTY = frozenset(('PREREGISTERED_REPLICATION','NEW_ELIGIBLE_POPULATION',
                    'NEW_CONTROL','CHANGED_METHOD_WITH_REVIEW','TECHNICAL_PARITY'))
DECISIONS = ('evidence_against','inconclusive_low_support','inconclusive_censoring',
             'relative_only','needs_replication')

@dataclass(frozen=True)
class ExperimentCharter:
    experiment_id:str
    question:str
    mechanism:str
    primary_estimand:str
    control_definition:str
    falsification_rule:str
    decision_rule:str
    uncertainty_method:str
    multiplicity_plan:str
    causal_availability:str
    dependency_checks:str
    novelty_kind:str
    novelty_reason:str
    source_sha256:str
    selection_sha256:str
    protocol_sha256:str
    baseline_build_sha256:str
    prior_attempts_sha256:str
    negative_evidence_refs:tuple
    session_dates:tuple
    expected_units:int
    max_wall_seconds:int
    max_peak_rss_bytes:int
    minimum_resolved_per_origin:int
    minimum_active_session_fraction:float
    warmup_policy:str='PAST_ONLY_FULL_FROZEN_FORMATION'
    allowed_data_role:str='EXPLORATION'
    status:str='PROPOSED_UNAUTHORIZED'

    def validate(self):
        _id(self.experiment_id)
        for field in ('source_sha256','selection_sha256','protocol_sha256',
                      'baseline_build_sha256','prior_attempts_sha256'):
            _sha(getattr(self,field))
        for field in ('question','mechanism','primary_estimand','control_definition',
                      'falsification_rule','decision_rule','uncertainty_method',
                      'multiplicity_plan','causal_availability','dependency_checks','novelty_reason'):
            x=getattr(self,field)
            if not isinstance(x,str) or not 1<=len(x.strip())<=2048:
                raise ValueError('bounded explicit design field required: '+field)
        if self.novelty_kind not in NOVELTY:
            raise ValueError('new decision-relevant information or explicit replication purpose required')
        if self.status!='PROPOSED_UNAUTHORIZED' or self.allowed_data_role!='EXPLORATION':
            raise ValueError('charter is exploration-only and cannot approve itself')
        if self.warmup_policy!='PAST_ONLY_FULL_FROZEN_FORMATION':
            raise ValueError('preserve causal formation history; no shard cold starts')
        if type(self.session_dates) is not tuple or not 1<=len(self.session_dates)<=3 or len(set(self.session_dates))!=len(self.session_dates):
            raise ValueError('bounded future shard: 1..3 distinct research sessions')
        for s in self.session_dates:
            if not isinstance(s,str) or len(s)!=10 or date.fromisoformat(s).isoformat()!=s or date.fromisoformat(s)>=date(2026,10,1):
                raise ValueError('holdout dates are forbidden; research declarations are not source authority')
        if tuple(sorted(self.session_dates))!=self.session_dates:
            raise ValueError('chronological session declaration required')
        for field,low,high in (
            ('expected_units',1,3207600),('max_wall_seconds',1,900),
            ('max_peak_rss_bytes',1,4*1024**3),('minimum_resolved_per_origin',100,100000)):
            x=getattr(self,field)
            if type(x) is not int or not low<=x<=high:
                raise ValueError('finite conservative bound required: '+field)
        f=self.minimum_active_session_fraction
        if type(f) not in (int,float) or not .8<=f<=1:
            raise ValueError('minimum active-session fraction 0.8..1 required')
        if type(self.negative_evidence_refs) is not tuple or not 1<=len(self.negative_evidence_refs)<=16:
            raise ValueError('recall previous negatives and inconclusive attempts')
        for s in self.negative_evidence_refs:_sha(s)
        if len(set(self.negative_evidence_refs))!=len(self.negative_evidence_refs):
            raise ValueError('unique negative-evidence references required')

def review_charter(charter, context):
    charter.validate()
    handoff=learning_handoff(context,episode_id=charter.experiment_id,purpose='discriminating experiment design')
    if context['question']!=charter.question:
        raise ValueError('charter and knowledge question mismatch')
    blockers=[]
    if context.get('edge_brain') is None: blockers.append('BIND_CANONICAL_BRAIN_NEGATIVE_RECALL')
    if context.get('literature') is None: blockers.append('BIND_CANONICAL_LITERATURE')
    if (context.get('edge_brain') or {}).get('invalidations'):
        blockers.append('REVIEW_INVALIDATED_DEPENDENCIES')
    data=asdict(charter)
    out=dict(schema='research_ops_experiment_charter_review_v1',
             status='BLOCKED_KNOWLEDGE_INTEGRATION' if blockers else 'READY_FOR_INDEPENDENT_REVIEW_NOT_EXECUTION',
             charter_sha256=digest(data),knowledge_context_sha256=context['context_sha256'],
             blockers=blockers,allowed_closeout_decisions=list(DECISIONS),
             rubric=['dependency readiness','uncertainty resolved by a falsifiable contrast',
                     'previous negatives and trial lineage retained','bounded cost'],
             calibrated_information_gain=False,source_authority_verified=False,
             budget_reserved=False,execution_allowed=False,holdout_allowed=False,
             promotion_allowed=False,learning_handoff=handoff)
    out['review_sha256']=digest(out)
    return out