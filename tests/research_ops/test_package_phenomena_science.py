import unittest,json
from pathlib import Path
from unittest.mock import patch
from tools.research_ops.confluence.package_phenomena_science import build_request,PLAN
ROOT=Path(__file__).resolve().parents[2]
URL='https://storage.googleapis.com/kagglesdsdata/datasets/SYNTHETIC/MNQ/MNQ_09-26_ticks_ext.parquet?TEST_ONLY'
class PackageScienceTests(unittest.TestCase):
 def test_compile_private_cpu_and_truthful_outcomes(self):
  q,r=build_request(ROOT,url=URL,source_commit='a'*40);t=q['request']['text'];compile(t,'science','exec');self.assertIn('confluence.phenomena_science_pilot',t);self.assertIn('/phenomena-response-pilot',t);self.assertIn('science-receipt.json',t);self.assertIn("state['outcomes_computed']=True",t);self.assertTrue(q['request']['isPrivate']);self.assertFalse(q['request']['enableGpu']);self.assertFalse(q['request']['enableTpu']);self.assertNotIn(URL,json.dumps(r));self.assertTrue(r['outcomes_requested']);self.assertFalse(r['confirmation'])
 def test_no_wrong_url_or_uncommitted_build(self):
  with self.assertRaises(ValueError):build_request(ROOT,url=URL.replace('storage.googleapis.com','evil.test'),source_commit='a'*40)
  with self.assertRaises(ValueError):build_request(ROOT,url=URL,source_commit='main')
 def test_changed_scientific_gate_rejected(self):
  p=json.loads((ROOT/PLAN).read_bytes());p['max_gap_ns']=10000000000
  with patch('tools.research_ops.confluence.package_phenomena_science.json.loads',return_value=p):
   with self.assertRaises(ValueError):build_request(ROOT,url=URL,source_commit='a'*40)
 def test_no_inference_or_zones_in_this_pilot(self):
  p=json.loads((ROOT/PLAN).read_bytes())
  for k in ('inference','holdout','pnl','fit_models','zone_detectors'):
   q={**p,k:True}
   with patch('tools.research_ops.confluence.package_phenomena_science.json.loads',return_value=q):
    with self.assertRaises(ValueError):build_request(ROOT,url=URL,source_commit='a'*40)
if __name__=='__main__':unittest.main()
