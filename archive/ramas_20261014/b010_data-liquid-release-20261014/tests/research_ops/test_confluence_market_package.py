import json,tempfile,unittest
from pathlib import Path
from tools.research_ops.confluence.package_market_pilot import build_request,BOOT
class MarketPackageTests(unittest.TestCase):
    def test_private_bounded_source_pinned_package_includes_all_runtime_modules(self):
        root=Path(__file__).resolve().parents[2];pin=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_PLAN.json').read_bytes())['pin'];url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/'+pin['file']+'?X-Goog-Signature=PRIVATE_PLACEHOLDER'
        request,r=build_request(root,url=url,source_commit='a'*40);self.assertTrue(request['request']['isPrivate']);self.assertFalse(request['request']['enableGpu']);self.assertNotIn('PRIVATE_PLACEHOLDER',json.dumps(r));self.assertIn('tools/research_ops/confluence/session_primitives.py',r['code_files_sha256']);self.assertIn('tools/research_ops/confluence/bt2a_stream.py',r['code_files_sha256']);compile(request['request']['text'],'private-package','exec')
    def test_invalid_transport_host_rejected(self):
        root=Path(__file__).resolve().parents[2]
        with self.assertRaises(ValueError):build_request(root,url='https://example.com/data',source_commit='a'*40)
    def test_raw_and_private_event_outputs_never_in_working_output_paths(self):
        self.assertIn("root/'captures-private.sqlite'",(Path(__file__).resolve().parents[2]/'tools/research_ops/confluence/market_pilot.py').read_text().replace("Path(private_root)/'captures-private.sqlite'","root/'captures-private.sqlite'"));self.assertIn("root/'pilot-private.log'",BOOT);self.assertNotIn('source-footer-receipt',BOOT)
if __name__=='__main__':unittest.main()
