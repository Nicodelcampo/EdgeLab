import unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
from tools.research_ops.confluence.package_phenomena_p0 import build_request,PLAN
ROOT=Path(__file__).resolve().parents[2]
URL='https://storage.googleapis.com/kagglesdsdata/datasets/SYNTHETIC/MNQ/MNQ_09-26_ticks_ext.parquet?TEST_ONLY'
class PackageP0Tests(unittest.TestCase):
 def test_compile_and_privacy(self):
  req,receipt=build_request(ROOT,url=URL,source_commit='a'*40);r=req['request'];compile(r['text'],'P0','exec')
  self.assertTrue(r['isPrivate']);self.assertFalse(r['enableGpu']);self.assertFalse(receipt['signed_url_published']);self.assertNotIn(URL,json.dumps(receipt));self.assertIn('feature-store-private',r['text']);self.assertNotIn('features-private.jsonl',r['text'])
 def test_reject_bad_source_url(self):
  with self.assertRaises(ValueError):build_request(ROOT,url=URL.replace('storage.googleapis.com','evil.test'),source_commit='a'*40)
 def test_reject_fake_commit(self):
  with self.assertRaises(ValueError):build_request(ROOT,url=URL,source_commit='main')
 def test_reject_outcomes_or_changed_limits(self):
  plan=json.loads((ROOT/PLAN).read_bytes())
  for k,v in [('outcomes',True),('classify_states',True),('wall_seconds',901)]:
   p={**plan,k:v}
   with patch('tools.research_ops.confluence.package_phenomena_p0.json.loads',return_value=p):
    with self.assertRaises(ValueError):build_request(ROOT,url=URL,source_commit='a'*40)
if __name__=='__main__':unittest.main()
