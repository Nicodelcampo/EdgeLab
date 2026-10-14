"""Semantic representation optimization; no native calculation is omitted."""
import json,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from dataclasses import replace
import numpy as np
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge import bars as B
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey
from tools.research_ops.confluence.detector_capture import Capture
from tools.research_ops.confluence.session_primitives import SessionTape
from tools.research_ops.confluence.cross_family_scene import CrossFamilyScene
from tools.research_ops.confluence.cross_family_collector import CrossFamilyCollector
from tools.research_ops.confluence.cross_family_pilot import PLAN,ROSTER
from test_confluence_detector_capture import trap_tape
ROOT=Path(__file__).resolve().parents[2]
class RetentionTests(unittest.TestCase):
 def setUp(self):self.plan=json.loads((ROOT/PLAN).read_bytes());self.roster=json.loads((ROOT/ROSTER).read_bytes())
 def test_dense_synthetic_all_and_mutations_only_identical_contexts(self):
  t=trap_tape(10501);t.ts_ns=int(np.datetime64('2026-06-15T00:00:00','ns').astype(np.int64))+np.arange(len(t),dtype=np.int64)*100000000;st=SessionTape(t,0,None,int(B.session_ids(t.ts_ns)[0]));out=[];counts=[]
  for mode in (False,True):
   scene=CrossFamilyScene(self.roster,self.plan,semantic_capture_only=mode);events,diag=scene.session(st,'2026-06-15',retain=True);scene.finish();c=CrossFamilyCollector(st,'2026-06-15',events,self.roster,{**self.plan,'max_common_anchors_per_session':40})
   for i in range(800,8000,250):
    row={'timestamp_ns':int(t.ts_ns[i]),'sequence':int(t.sequence[i]),'windows':{'20':{'pressure_ratio':1.2,'trade_count_ratio':.8,'directed_progress_ticks':1.,'direction_from_prior':1}}};c(row,i,4)
   z,meta=c.finish(c.n);out.append(z.copy());counts.append(diag)
  np.testing.assert_array_equal(*out);self.assertLess(counts[1]['capture_records_retained'],counts[0]['capture_records_retained'])
  for a,b in zip(counts[0]['config_counts'],counts[1]['config_counts']):
   for kind in ('BIRTH','REMOVE','TOUCH','CLASSIFY'):self.assertEqual(a.get(kind,0),b.get(kind,0))
 def test_touch_flood_still_processed_and_counted_without_using_mutation_capacity(self):
  t=trap_tape(31);date='2026-09-01';st=SessionTape(t,0,None,int(B.session_ids(t.ts_ns)[0]));plan={**self.plan,'max_session_capture_records':2};config=self.roster['configs'][3];key=ZoneKey('BT2',config['config_sha256'],'b'*64,'synthetic')
  def delta(feed):
   e=Capture('TOUCH',key,feed.available,feed.consumed_tick_index,feed.bar,190,210,1,());return SimpleNamespace(records=(e,)*10,unavailable_events=0)
  with patch('tools.research_ops.confluence.bt2_stream.BT2Stream.push',side_effect=delta):
   scene=CrossFamilyScene(self.roster,plan)
   with self.assertRaisesRegex(ValueError,'nine config capture capacity'):scene.session(st,date,retain=True)
  with patch('tools.research_ops.confluence.bt2_stream.BT2Stream.push',side_effect=delta):
   scene=CrossFamilyScene(self.roster,plan,semantic_capture_only=True);events,diag=scene.session(st,date,retain=True);self.assertEqual(diag['capture_records_retained'],0);self.assertGreater(sum(c.get('TOUCH',0) for c in diag['config_counts']),0)
 def test_actual_mutation_capacity_is_not_relaxed(self):
  t=trap_tape(31);st=SessionTape(t,0,None,int(B.session_ids(t.ts_ns)[0]));config=self.roster['configs'][3];key=ZoneKey('BT2',config['config_sha256'],'b'*64,'synthetic')
  def delta(feed):
   e=Capture('BIRTH',key,feed.available,feed.consumed_tick_index,feed.bar,190,210,1,());return SimpleNamespace(records=(e,)*10,unavailable_events=0)
  with patch('tools.research_ops.confluence.bt2_stream.BT2Stream.push',side_effect=delta):
   scene=CrossFamilyScene(self.roster,{**self.plan,'max_session_capture_records':2},semantic_capture_only=True)
   with self.assertRaisesRegex(ValueError,'nine config capture capacity'):scene.session(st,'2026-09-01',retain=True)
if __name__=='__main__':unittest.main()
