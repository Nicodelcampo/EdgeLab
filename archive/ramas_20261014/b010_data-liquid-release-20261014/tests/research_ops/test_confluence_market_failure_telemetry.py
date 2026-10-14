import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.research_ops.confluence.market_pilot import main
class FailureTelemetryTests(unittest.TestCase):
    def test_fixed_budget_category_and_unknown_error_without_raw_text(self):
        root=Path(__file__).resolve().parents[2]
        for message,category in [('private capture budget; no truncation','PRIVATE_CAPTURE_RECORD_BUDGET'),('untrusted raw price=987654321 secret_blob','UNCLASSIFIED_ENGINE_ERROR')]:
            with tempfile.TemporaryDirectory() as d:
                td=Path(d);folder=td/'docs/research/ops';folder.mkdir(parents=True)
                for name in ('MNQ_CONFLUENCE_MARKET_PILOT_PLAN.json','MNQ_CONFLUENCE_MARKET_PILOT_RETRY_PLAN.json','MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json'):(folder/name).write_bytes((root/'docs/research/ops'/name).read_bytes())
                with patch('sys.argv',['pilot','--source',str(td/'no-market.parquet'),'--root',str(td),'--out',str(td/'pilot-receipt.json')]),patch('tools.research_ops.confluence.market_pilot.run_pilot',side_effect=ValueError(message)),patch.object(Path,'is_dir',return_value=True):
                    with self.assertRaises(SystemExit):main()
                text=(td/'failure-receipt.json').read_text();r=json.loads(text);self.assertEqual(r['failure_category'],category);self.assertNotIn(message,text);self.assertFalse(r['raw_payload_exported']);self.assertFalse(r['outcomes_or_edge_claim'])
    def test_bootstrap_seals_failure_receipt_and_includes_retry_budget(self):
        from tools.research_ops.confluence.package_market_pilot import BOOT,build_request
        root=Path(__file__).resolve().parents[2];pin=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_RETRY_PLAN.json').read_bytes())['pin'];req,r=build_request(root,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/'+pin['file'],source_commit='a'*40)
        self.assertIn('failure_receipt_sha256',BOOT);self.assertIn('docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_RETRY_PLAN.json',r['code_files_sha256']);compile(req['request']['text'],'retry-bootstrap','exec')
if __name__=='__main__':unittest.main()
