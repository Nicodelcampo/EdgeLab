import json,unittest
from pathlib import Path
import numpy as np
from tools.research_ops.confluence.multiasset_crossfamily import validate_plan,FOCUS_PLAN
from tools.research_ops.confluence.gc_focused_summary import FocusedSummary
import test_cross_family_streaming as streaming_tests
from tools.research_ops.confluence.cross_family_streaming import StreamingScene
from tools.research_ops.confluence.cross_family_collector import CrossFamilyCollector
ROOT=Path(__file__).resolve().parents[2]
class FocusTests(unittest.TestCase):
 def setUp(self):self.plan=json.loads((ROOT/FOCUS_PLAN).read_bytes())
 def test_exact_pair_and_calendar_mutations_rejected(self):
  _,r=validate_plan(self.plan,'GC');self.assertEqual(len(r['configs']),2);self.assertEqual(len(r['pairs']),1)
  self.assertEqual(r['configs'][0]['indicator'],'avolzonepoi2')
  for key,value in [('max_gap_ns',11000000000),('evaluation_sessions',['2026-10-01']),('focus_pair_sha256','0'*64)]:
   q={**self.plan,key:value}
   with self.assertRaises(ValueError):validate_plan(q,'GC')
  with self.assertRaises(ValueError):validate_plan(self.plan,'ES')
 def test_subset_tensor_equals_original_pair_with_full_history(self):
  helper=streaming_tests.StreamingTests();helper.setUp();_,r=validate_plan(self.plan,'GC');out=[]
  for roster in (helper.roster,r):
   scene=StreamingScene(roster,helper.plan);zs=[]
   for j,st in enumerate(helper.tapes()):
    date=np.datetime64(st.session_id*86400,'s').astype(str)[:10];e,_=scene.session(st,date,retain=j>=22)
    if j>=22:
     c=CrossFamilyCollector(st,date,e,roster,helper.plan);helper.measured(c,st.ticks);e.finish();z,_=c.finish(c.n);zs.append(z[:,:,2:3].copy() if len(roster['pairs'])==18 else z.copy())
   scene.finish();out.append(zs)
  for a,b in zip(*out):np.testing.assert_array_equal(a,b)
 def test_session_weights_empty_cuts_and_thinning_before_cut(self):
  f=FocusedSummary(self.plan);z=np.zeros((25,43));z[:,11]=z[:,29]=z[:,36]=1;loss={k:np.full(25,v) for k,v in [('CONTINUOUS',1.),('ARRIVAL',.9),('ARRIVAL_CC',.95),('DENSITY',.85),('INTERACTION',1.1),('MIRROR_FULL',1.05)]}
  f.begin('2026-08-27',np.arange(25,dtype=np.int64)*5000000000);f.add(0,z,loss);o=f.finish();self.assertEqual(o['groups']['RETURN_THIN60S']['anchors'],3);self.assertEqual(o['groups']['NOT_RETURN']['support_sessions'],0);self.assertFalse(o['groups']['RETURN']['support_screen_passed_not_edge']);self.assertAlmostEqual(o['groups']['RETURN']['contrasts']['ARRIVAL_MINUS_DENSITY']['equal_session_mean'],.05)
  with self.assertRaises(ValueError):f.begin('x',np.array([1,1]))
