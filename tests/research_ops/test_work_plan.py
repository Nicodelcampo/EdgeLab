"""Metadata-only work-plan tests; all pins are synthetic test fixtures."""
import unittest
from dataclasses import replace
from tools.research_ops.work_plan import CampaignIdentity,build_work_plan,validate_checkpoint_identity,validate_work_plan

class WorkPlanTests(unittest.TestCase):
    def identity(self):return CampaignIdentity('MNQ_12-25',*['a'*64,'b'*64,'c'*64,'d'*64,'e'*64,'f'*64])
    def plan(self,identity=None,**kw):return build_work_plan(identity or self.identity(),**dict(max_attempts=18,seconds_per_attempt=600,memory_bytes_per_worker=4*1024**3,**kw))
    def receipt(self,p):return dict(unit_id=p['units'][0]['unit_id'],fingerprint=p['units'][0]['fingerprint'],output_sha256='0'*64)
    def test_exact_eighteen_families(self):
        p=self.plan();self.assertEqual(len(p['units']),18);self.assertEqual(len(set(u['unit_id'] for u in p['units'])),18);self.assertEqual(p['units'][0]['spec']['family'],'P80_W5_R8_1000_20');self.assertEqual(p['units'][-1]['spec']['family'],'P80_W10_R18_3000_20')
    def test_deterministic(self):self.assertEqual(self.plan(),self.plan())
    def test_scientific_fingerprint_not_changed_by_resource_budget(self):
        a=self.plan();b=build_work_plan(self.identity(),max_attempts=36,seconds_per_attempt=1,memory_bytes_per_worker=1024);self.assertEqual([u['fingerprint'] for u in a['units']],[u['fingerprint'] for u in b['units']])
    def test_all_identity_fields_invalidate(self):
        a=self.plan()
        for key in ('source_sha256','selection_sha256','code_sha256','protocol_sha256','authorization_sha256','risk_review_sha256'):
            b=self.plan(replace(self.identity(),**{key:'9'*64}));self.assertNotEqual(a['units'][0]['fingerprint'],b['units'][0]['fingerprint'])
    def test_other_contract_isolated(self):self.assertNotEqual(self.plan()['units'][0]['fingerprint'],self.plan(replace(self.identity(),contract='MNQ_03-26'))['units'][0]['fingerprint'])
    def test_disabled_all_units(self):
        p=self.plan();self.assertIs(p['execution_allowed'],False);self.assertTrue(all(not u['complete'] and u['status']=='PLANNED_UNAUTHORIZED' for u in p['units']))
    def test_budget_required_and_bounded(self):
        for name,value in [('max_attempts',17),('max_attempts',37),('max_attempts',True),('seconds_per_attempt',0),('seconds_per_attempt',86401),('memory_bytes_per_worker',True)]:
            args=dict(max_attempts=18,seconds_per_attempt=600,memory_bytes_per_worker=4096);args[name]=value
            with self.assertRaises(ValueError):build_work_plan(self.identity(),**args)
    def test_invalid_identity(self):
        for key,value in [('contract','../MNQ_12-25'),('contract','ES_12-25'),('code_sha256','unknown')]:
            with self.assertRaises(ValueError):self.plan(replace(self.identity(),**{key:value}))
    def test_receipt_identity_not_completion(self):
        p=self.plan();out=validate_checkpoint_identity(p,self.receipt(p));self.assertIs(out['completion_verified'],False);self.assertIs(out['skip_allowed'],False)
    def test_wrong_receipt_identity(self):
        p=self.plan();r=self.receipt(p);r['fingerprint']='0'*64
        with self.assertRaises(ValueError):validate_checkpoint_identity(p,r)
    def test_legacy_log_not_receipt(self):
        with self.assertRaises(ValueError):validate_checkpoint_identity(self.plan(),{'status':'FAMILY','family':'P80_W5_R8_1000_20'})
    def test_no_completion_extra_field(self):
        p=self.plan();r=self.receipt(p);r['complete']=True
        with self.assertRaises(ValueError):validate_checkpoint_identity(p,r)
    def test_invalid_output_digest(self):
        p=self.plan();r=self.receipt(p);r['output_sha256']='bad'
        with self.assertRaises(ValueError):validate_checkpoint_identity(p,r)

    def test_mutated_family_rejected(self):
        p=self.plan();p['units'][0]['spec']['racimo_window']=5000
        with self.assertRaises(ValueError):validate_work_plan(p)
    def test_mutated_fingerprint_rejected(self):
        p=self.plan();p['units'][0]['fingerprint']='0'*64
        with self.assertRaises(ValueError):validate_checkpoint_identity(p,self.receipt(p))
    def test_mutated_completion_rejected(self):
        p=self.plan();p['units'][0]['complete']=True
        with self.assertRaises(ValueError):validate_work_plan(p)
    def test_valid_plan_not_authority(self):
        self.assertIs(validate_work_plan(self.plan())['authority_authenticated'],False)
