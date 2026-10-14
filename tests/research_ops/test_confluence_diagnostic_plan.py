import json,unittest
from pathlib import Path
from tools.research_ops.confluence.package_market_pilot import build_request
from tools.research_ops.confluence.build_target_free_pilot import digest
class DiagnosticPlanTests(unittest.TestCase):
    def test_preserves_scope_history_and_resource_limits(self):
        root=Path(__file__).resolve().parents[2];folder=root/'docs/research/ops';old=json.loads((folder/'MNQ_CONFLUENCE_MARKET_PILOT_RETRY_PLAN.json').read_bytes());new=json.loads((folder/'MNQ_CONFLUENCE_MARKET_DIAGNOSTIC_PLAN.json').read_bytes())
        mutable={'schema','implementation_attempt','retry_reason','compact_storage_candidate_activated','partial_receipts_enabled'}
        self.assertEqual({k:v for k,v in old.items() if k not in mutable},{k:v for k,v in new.items() if k not in mutable});self.assertEqual(new['implementation_attempt'],3);self.assertFalse(new['compact_storage_candidate_activated']);self.assertTrue(new['partial_receipts_enabled'])
    def test_package_binds_diagnostic_plan_and_does_not_bundle_candidate(self):
        root=Path(__file__).resolve().parents[2];plan=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_MARKET_DIAGNOSTIC_PLAN.json').read_bytes());q,r=build_request(root,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/'+plan['pin']['file'],source_commit='a'*40)
        self.assertEqual(r['plan_sha256'],digest(plan));self.assertIn('tools/research_ops/confluence/failure_telemetry.py',r['code_files_sha256']);self.assertNotIn('tools/research_ops/confluence/compact_store.py',r['code_files_sha256']);self.assertIn('partial_receipt_sha256',q['request']['text']);self.assertIn('MNQ_CONFLUENCE_MARKET_DIAGNOSTIC_PLAN.json',q['request']['text'])
if __name__=='__main__':unittest.main()
