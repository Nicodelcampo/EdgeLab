import json,hashlib,tempfile,unittest
from pathlib import Path
from tools.research_ops.remote_watch import RemoteWatch
from tools.research_ops.confluence.terminal_acquisition import acquisition_plan,review_failure,MAX_BYTES
from tools.research_ops.confluence.build_target_free_pilot import digest
from tools.research_ops.confluence.failure_telemetry import diagnostic
class TerminalTests(unittest.TestCase):
    def fixture(self):
        plan={'target_session':'2026-06-16','max_session_ticks':5000,'max_total_ticks':10000,'max_capture_records':100}
        pkg={'source_commit':'a'*40,'bundle_sha256':'b'*64,'plan_sha256':digest(plan)}
        f={'schema':'mnq_confluence_market_failure_v1','status':'FAILED_NO_COMPLETE_CENSUS','failure_category':'UNCLASSIFIED_ENGINE_ERROR','plan_sha256':digest(plan),'holdout_opened':False,'raw_payload_exported':False,'outcomes_or_edge_claim':False}
        b={**pkg,'status':'MARKET_PILOT_FAILED_NO_EDGE_CLAIM','exit_code':1,'stop_reason':None,'failure_category':f['failure_category']}
        for k in ('holdout_opened','outcomes_computed','pnl_computed','raw_exported','source_quality_certified','new_dataset_quality_audit'):b[k]=False
        return b,f,pkg,plan
    def call(self,b,f,pkg,plan,progress=b'SESSION_COMPLETE 2026-06-16 100 90\nGEOMETRY_TRIAD_COMPLETE 0\nPILOT_FAILED UNCLASSIFIED_ENGINE_ERROR\n'):
        fb=json.dumps(f).encode();b=dict(b,failure_receipt_sha256=hashlib.sha256(fb).hexdigest());return review_failure(json.dumps(b).encode(),fb,progress,package=pkg,plan=plan)
    def test_failure_not_success(self):
        r=self.call(*self.fixture());self.assertEqual(r['geometry_triads_reported_complete'],[0]);self.assertFalse(r['scientific_results_or_edge_verified']);self.assertFalse(r['automatic_retry_allowed'])
    def test_wrong_binding(self):
        b,f,p,plan=self.fixture();b['source_commit']='c'*40
        with self.assertRaises(ValueError):self.call(b,f,p,plan)
    def test_unknown_receipt_fields(self):
        b,f,p,plan=self.fixture();f['raw']='price secret'
        with self.assertRaises(ValueError):self.call(b,f,p,plan)
    def test_scope_and_plan(self):
        for field in ('scope','plan'):
            b,f,p,plan=self.fixture()
            if field=='scope':f['holdout_opened']=True
            else:f['plan_sha256']='f'*64
            with self.assertRaises(ValueError):self.call(b,f,p,plan)
    def test_progress_rejects_raw_and_partial_success(self):
        for progress in (b'raw price 555\n',b'SESSION_COMPLETE 2026-06-16 100 90\nGEOMETRY_TRIAD_COMPLETE 1\n',b'SESSION_COMPLETE 2026-10-01 100 90\n',b'SESSION_COMPLETE 2026-06-16 100 101\n',b'PILOT_FAILED UNCLASSIFIED_ENGINE_ERROR\nSESSION_COMPLETE 2026-06-16 100 90\n'):
            with self.assertRaises(ValueError):self.call(*self.fixture(),progress)
    def test_seal_and_oversize(self):
        b,f,p,plan=self.fixture();b['failure_receipt_sha256']='f'*64
        with self.assertRaises(ValueError):review_failure(json.dumps(b).encode(),json.dumps(f).encode(),b'',package=p,plan=plan)
        with self.assertRaises(ValueError):review_failure(b' '*(MAX_BYTES+1),b'{}',b'',package=p,plan=plan)
    def test_sanitized_exception(self):
        try:raise ValueError('price=12345 SECRET')
        except Exception as exc:r=diagnostic(exc)
        self.assertNotIn('12345',json.dumps(r));self.assertEqual(r['exception_type'],'ValueError');self.assertEqual(r['exception_site'],'UNCLASSIFIED_SITE')
    def test_more_budget_categories(self):
        self.assertEqual(diagnostic(ValueError('candidate triple budget exceeded; no truncation'))['failure_category'],'CANDIDATE_TRIPLE_BUDGET')
    def test_plan_rejects_running_and_wrong_version(self):
        i={'account':'nico','kernel_id':1,'version':2,'source_commit':'a'*40,'bundle_sha256':'b'*64,'plan_sha256':'c'*64}
        with tempfile.TemporaryDirectory() as d:
            w=RemoteWatch(Path(d)/'watch');s=w.initialize();s=w.register(i,expected_tip=s['tip_sha256'])
            with self.assertRaises(ValueError):acquisition_plan(s,i)
            s=w.reserve(i,expected_tip=s['tip_sha256']);s=w.record(i,ticket=s['ticket'],status='ERROR',response_sha256='d'*64,expected_tip=s['tip_sha256']);p=acquisition_plan(s,i)
            self.assertEqual(p['max_files'],4);self.assertFalse(p['download_all_allowed']);self.assertFalse(p['inventory_completeness_inferred'])
            with self.assertRaises(KeyError):acquisition_plan(s,dict(i,version=3))
if __name__=='__main__':unittest.main()
