import unittest
from dataclasses import replace
from tools.research_ops.experiment_charter import ExperimentCharter, review_charter
from tools.research_ops.knowledge import knowledge_context

class CharterTests(unittest.TestCase):
    def setUp(self):
        self.c=ExperimentCharter('future_shard','Which explanation survives a fixed control?','A causal mechanism to falsify','Paired difference','Fixed geometry and context control','Negative result invalidates this explanation','No winner forced; retain uncertainty','Predeclared dependence-aware interval','All attempts and alias lineage retained','Prefix available at trigger','Source, warmup and lineage gates','NEW_CONTROL','Discriminates censoring from geometry','a'*64,'b'*64,'c'*64,'d'*64,'e'*64,('f'*64,),('2026-06-01','2026-06-02'),100,300,2**30,100,.8)
        self.context=knowledge_context(self.c.question,None,None)
    def test_valid_missing_sources_blocked(self):
        out=review_charter(self.c,self.context)
        self.assertEqual(out['status'],'BLOCKED_KNOWLEDGE_INTEGRATION')
        self.assertFalse(out['execution_allowed']);self.assertFalse(out['calibrated_information_gain'])
    def test_linked_sources_still_not_execution(self):
        brain=dict(query=self.c.question,claims_are_evidence=False,hits=[],invalidations={},used_chars=0)
        literature=dict(query=self.c.question,claims_are_evidence=False,items=[],used_chars=0)
        out=review_charter(self.c,knowledge_context(self.c.question,brain,literature))
        self.assertEqual(out['status'],'READY_FOR_INDEPENDENT_REVIEW_NOT_EXECUTION')
        self.assertFalse(out['source_authority_verified']);self.assertFalse(out['budget_reserved'])
    def test_holdout_forbidden(self):
        for dates in (('2026-10-01',),('2026-12-01',)):
            with self.subTest(dates=dates),self.assertRaises(ValueError):replace(self.c,session_dates=dates).validate()
    def test_no_self_approval(self):
        with self.assertRaises(ValueError):replace(self.c,status='APPROVED').validate()
    def test_confirmation_role_forbidden(self):
        with self.assertRaises(ValueError):replace(self.c,allowed_data_role='CONFIRMATION_RESERVED').validate()
    def test_negative_history_required(self):
        with self.assertRaises(ValueError):replace(self.c,negative_evidence_refs=()).validate()
    def test_trial_history_pin_required(self):
        with self.assertRaises(ValueError):replace(self.c,prior_attempts_sha256='').validate()
    def test_no_unchanged_repeat_without_purpose(self):
        with self.assertRaises(ValueError):replace(self.c,novelty_kind='NONE').validate()
    def test_explicit_replication_allowed_but_unapproved(self):
        out=review_charter(replace(self.c,novelty_kind='PREREGISTERED_REPLICATION'),self.context)
        self.assertFalse(out['execution_allowed'])
    def test_cold_shard_not_equivalent(self):
        with self.assertRaises(ValueError):replace(self.c,warmup_policy='COLD_START').validate()
    def test_budget_bounds(self):
        for field,value in [('max_wall_seconds',901),('max_peak_rss_bytes',0),('expected_units',True),('minimum_resolved_per_origin',99),('minimum_active_session_fraction',.5)]:
            with self.subTest(field=field),self.assertRaises(ValueError):replace(self.c,**{field:value}).validate()
    def test_nan_fraction(self):
        with self.assertRaises(ValueError):replace(self.c,minimum_active_session_fraction=float('nan')).validate()
    def test_shard_bound(self):
        with self.assertRaises(ValueError):replace(self.c,session_dates=('2026-01-01','2026-01-02','2026-01-03','2026-01-04')).validate()
    def test_invalid_session_date(self):
        with self.assertRaises(ValueError):replace(self.c,session_dates=('2026-02-31',)).validate()
    def test_duplicate_sessions(self):
        with self.assertRaises(ValueError):replace(self.c,session_dates=('2026-01-01','2026-01-01')).validate()
    def test_unsorted_sessions(self):
        with self.assertRaises(ValueError):replace(self.c,session_dates=('2026-01-02','2026-01-01')).validate()
    def test_duplicate_negative_pins(self):
        with self.assertRaises(ValueError):replace(self.c,negative_evidence_refs=('f'*64,'f'*64)).validate()
    def test_no_relaxed_uncertainty_after_outcome(self):
        with self.assertRaises(ValueError):replace(self.c,uncertainty_method='').validate()
    def test_question_binding(self):
        with self.assertRaises(ValueError):review_charter(self.c,knowledge_context('different',None,None))
    def test_context_tamper(self):
        self.context['gaps']=[]
        with self.assertRaises(ValueError):review_charter(self.c,self.context)
    def test_invalidations_remain_blocker(self):
        brain=dict(query=self.c.question,claims_are_evidence=False,hits=[],invalidations={'x':'STALE'},used_chars=0)
        out=review_charter(self.c,knowledge_context(self.c.question,brain,None))
        self.assertIn('REVIEW_INVALIDATED_DEPENDENCIES',out['blockers'])
    def test_no_promotion_decision(self):
        out=review_charter(self.c,self.context)
        self.assertNotIn('validated_under_protocol',out['allowed_closeout_decisions'])
        self.assertFalse(out['promotion_allowed'])

if __name__=='__main__':unittest.main()