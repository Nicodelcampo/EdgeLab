import json,unittest
from pathlib import Path
from tools.research_ops.confluence.bt2a_rolling_benchmark import PLAN,validate
from tools.research_ops.confluence.package_gc_rolling import build_request
class RollingPackageTests(unittest.TestCase):
 def test_closed_plan_and_package_no_outcomes_or_promotion(self):
  root=Path(__file__).resolve().parents[2];p=json.loads((root/PLAN).read_bytes());validate(p,'GC')
  for k in ('automatic_promotion','production_default_changed','outcomes'):
   with self.assertRaises(ValueError):validate({**p,k:True},'GC')
  q,r=build_request(root,url='https://storage.googleapis.com/kagglesdsdata/datasets/test/GC/GC_12-26_ticks_ext.parquet',source_commit='a'*40);self.assertIn('confluence.bt2a_rolling_benchmark',q['request']['text']);self.assertIn('tools/research_ops/confluence/rolling_native_percentile.py',r['files_sha256']);self.assertFalse(r['outcomes_requested'])
