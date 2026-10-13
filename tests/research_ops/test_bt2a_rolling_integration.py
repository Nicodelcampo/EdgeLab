import unittest
import test_cross_family_streaming as helper
from tools.research_ops.confluence.bt2a_stream import BT2AStream,TickChunk
from tools.research_ops.confluence.bt2a_footprint_cache import BucketFootprintCache
from tools.research_ops.confluence.bt2a_multisession_profile import fingerprint,measure
import numpy as np
class IntegrationTests(unittest.TestCase):
 def test_multisession_all_native_captures_threshold_logs_state_exact(self):
  h=helper.StreamingTests();h.setUp();tapes=h.tapes(days=3);configs=[c for c in h.roster['configs'] if c['indicator']=='bigtrap2absorption']
  for size in (.1,.25,.00005,.03125):
   for c in configs:
    ss=[BT2AStream(params=c['params'],tick_size=size,collect_diagnostics=True,footprint_cache=BucketFootprintCache(),rolling_percentile=r) for r in (False,True)];offset=0;records=[[],[]];u=[0,0]
    for st in tapes:
     t=st.ticks;ids=np.full(len(t),st.session_id,dtype=np.int64)
     for j in range(0,len(t),137):
      z=min(len(t),j+137);ch=TickChunk(*(getattr(t,n)[j:z] for n in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),ids[j:z],offset+j)
      for k,s in enumerate(ss):d=s.push(ch);records[k].extend(d.records);u[k]+=d.unavailable_events
     self.assertEqual(fingerprint(ss[0]),fingerprint(ss[1]));self.assertEqual(ss[0].log_hash.hexdigest(),ss[1].log_hash.hexdigest());cells=dict(zip(ss[1].flush.__code__.co_freevars,ss[1].flush.__closure__));self.assertEqual(list(ss[1].rolling_percentile.fifo),cells['abs_ring'].cell_contents);offset+=len(t)
    for k,s in enumerate(ss):d=s.finish();records[k].extend(d.records);u[k]+=d.unavailable_events
    self.assertEqual(records[0],records[1]);self.assertEqual(u[0],u[1]);self.assertEqual(fingerprint(ss[0]),fingerprint(ss[1]));self.assertEqual(ss[0].log_hash.hexdigest(),ss[1].log_hash.hexdigest())
 def test_benchmark_caller_exercises_both_algorithms_and_diagnostics(self):
  h=helper.StreamingTests();h.setUp();tapes=h.tapes(days=2);cs=[c for c in h.roster['configs'] if c['indicator']=='bigtrap2absorption']
  for diag in (False,True):
   a=measure(tapes,cs,.1,'PROFILE_SEQUENTIAL',rolling_percentile=False,collect_diagnostics=diag);b=measure(tapes,cs,.1,'PROFILE_SEQUENTIAL',rolling_percentile=True,collect_diagnostics=diag);self.assertEqual(a['profiles'],b['profiles']);self.assertEqual(a['session_state_sha256'],b['session_state_sha256'])
 def test_no_default_activation_or_silent_parameter_change(self):
  s=BT2AStream(params={},tick_size=.25);self.assertIsNone(s.rolling_percentile)
  with self.assertRaises(ValueError):BT2AStream(params={},tick_size=.25,rolling_percentile='yes')
