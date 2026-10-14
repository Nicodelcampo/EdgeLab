import unittest
from pathlib import Path
from tools.research_ops.confluence.package_gc_focused import build_request
class PackageTests(unittest.TestCase):
 def test_closed_purpose_and_benchmark_not_label_computation(self):
  root=Path(__file__).resolve().parents[2];url='https://storage.googleapis.com/kagglesdsdata/datasets/test/GC/GC_12-26_ticks_ext.parquet'
  science,_=build_request(root,url=url,source_commit='a'*40,purpose='SCIENCE');bench,_=build_request(root,url=url,source_commit='a'*40,purpose='SCHEDULE_BENCHMARK')
  self.assertIn("'outcomes_requested':False",bench['request']['text']);self.assertIn("state['outcomes_computed']=False",bench['request']['text']);self.assertNotIn("state['outcomes_computed']=True",bench['request']['text']);self.assertIn("'outcomes_requested':True",science['request']['text'])
  with self.assertRaises(ValueError):build_request(root,url=url,source_commit='a'*40,purpose='AUTO_SELECT')
