import json,unittest
from pathlib import Path
import test_cross_family_streaming as helper
from tools.research_ops.confluence.bt2a_multisession_profile import measure,validate,PLAN,fingerprint
from tools.research_ops.confluence.bt2a_stream import BT2AStream
class ProfileTests(unittest.TestCase):
 def test_persistent_native_state_exact_across_residual_sessions(self):
  h=helper.StreamingTests();h.setUp();tapes=h.tapes(days=3);cs=[c for c in h.roster['configs'] if c['indicator']=='bigtrap2absorption'];a=measure(tapes,cs,.1,'PROFILE_SEQUENTIAL');b=measure(tapes,cs,.1,'CHUNK_INTERLEAVED');self.assertEqual(a['profiles'],b['profiles']);self.assertEqual(a['session_state_sha256'],b['session_state_sha256'])
 def test_fingerprint_not_only_state_sizes(self):
  s=BT2AStream(params={},tick_size=.1);old=fingerprint(s);cells=dict(zip(s.flush.__code__.co_freevars,s.flush.__closure__));cells['abs_ring'].cell_contents.append(3.);new=fingerprint(s);cells['abs_ring'].cell_contents[0]=4.;self.assertNotEqual(new,fingerprint(s));self.assertNotEqual(old,new)
 def test_exact_plan_no_outcomes(self):
  p=json.loads((Path(__file__).resolve().parents[2]/PLAN).read_bytes());validate(p,'GC')
  with self.assertRaises(ValueError):validate({**p,'outcomes':True},'GC')
  with self.assertRaises(ValueError):validate(p,'ES')
