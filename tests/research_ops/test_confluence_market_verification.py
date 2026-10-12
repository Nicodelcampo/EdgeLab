import copy,hashlib,json,unittest
from pathlib import Path
from tools.research_ops.confluence.verify_market_pilot import verify
from tools.research_ops.confluence.build_target_free_pilot import digest

class VerificationTests(unittest.TestCase):
    def fixture(self):
        root=Path(__file__).resolve().parents[2];plan=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_PLAN.json').read_bytes());roster=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());package={'source_commit':'a'*40,'bundle_sha256':'b'*64}
        p={'status':'TARGET_FREE_MARKET_PILOT_COMPLETE_NOT_VALIDATED_EDGE','source_pin':plan['pin'],'plan_sha256':digest(plan),'roster_sha256':digest(roster),'contract':plan['contract'],'target_session':plan['target_session'],'configs_completed':96,'aligned_triads_completed':32,'target_ticks':10,'ticks_processed':20,'config_counts':[],'geometry_triads':[]}
        for k in ('full_cartesian_coverage','arrival_labels_evaluated','occupancy_nulls_evaluated','outcomes_evaluated','pnl_computed','holdout_opened','source_quality_certified','raw_ticks_or_events_exported','selection_by_outcomes','canonical_brain_written','inference_or_edge_claim'):p[k]=False
        for c in roster['configs']:p['config_counts'].append({**{k:c[k] for k in ('config_sha256','indicator','bar_spec')},'all_capture_counts':{'BIRTH':1},'target_capture_counts':{'BIRTH':1},'ordered_private_capture_sha256':'c'*64})
        families=[[c['config_sha256'] for c in roster['configs'] if c['indicator']==f] for f in ('avolzonepoi2','bigtrap2','bigtrap2absorption')]
        for i in range(32):p['geometry_triads'].append({'aligned_triad_index':i,'config_sha256':[f[i] for f in families],'target_geometry_counts':{}})
        boot={**package,'status':p['status'],'exit_code':0,'stop_reason':None,'transport_pin_verified':True}
        for k in ('holdout_opened','outcomes_computed','pnl_computed','raw_exported','source_quality_certified','new_dataset_quality_audit'):boot[k]=False
        return boot,p,package,plan,roster
    def call(self,b,p,package,plan,roster):
        pb=json.dumps(p).encode();b={**b,'pilot_receipt_sha256':hashlib.sha256(pb).hexdigest()};return verify(json.dumps(b).encode(),pb,package=package,plan=plan,roster=roster)
    def test_complete_declared_scope_binds_but_does_not_certify_edge(self):
        r=self.call(*self.fixture());self.assertEqual(r['coverage_checked_configs'],96);self.assertFalse(r['outcomes_or_edge_verified'])
    def test_wrong_triad_or_missing_config_rejected(self):
        for case in ('triad','config'):
            b,p,pkg,plan,r=self.fixture()
            if case=='triad':p['geometry_triads'][1]['config_sha256'][0]='x'
            else:p['config_counts'].pop()
            with self.assertRaises(ValueError):self.call(b,p,pkg,plan,r)
    def test_overclaim_and_budget_failure_rejected(self):
        b,p,pkg,plan,r=self.fixture();p['inference_or_edge_claim']=True
        with self.assertRaises(ValueError):self.call(b,p,pkg,plan,r)
        p['inference_or_edge_claim']=False;b['stop_reason']='RSS_LIMIT'
        with self.assertRaises(ValueError):self.call(b,p,pkg,plan,r)
    def test_physical_output_change_rejected(self):
        b,p,pkg,plan,r=self.fixture();pb=json.dumps(p).encode();b['pilot_receipt_sha256']='f'*64
        with self.assertRaises(ValueError):verify(json.dumps(b).encode(),pb,package=pkg,plan=plan,roster=r)
if __name__=='__main__':unittest.main()
