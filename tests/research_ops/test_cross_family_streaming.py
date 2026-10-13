"""Dense invented tapes: bounded prefixes vs full-session immutable reference."""
import json,unittest
from pathlib import Path
from datetime import date,timedelta
from types import SimpleNamespace
import numpy as np
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge import bars as B
from tools.research_ops.confluence.session_primitives import SessionTape
from tools.research_ops.confluence.asof_intersections import Clock
from tools.research_ops.confluence.cross_family_scene import CrossFamilyScene
from tools.research_ops.confluence.cross_family_streaming import StreamingScene
from tools.research_ops.confluence.cross_family_collector import CrossFamilyCollector
from tools.research_ops.confluence.cross_family_pilot import PLAN,ROSTER,fit_models,score
from tools.research_ops.confluence.phenomena_models import FEATURES
ROOT=Path(__file__).resolve().parents[2]
class StreamingTests(unittest.TestCase):
 def setUp(self):self.plan=json.loads((ROOT/PLAN).read_bytes());self.roster=json.loads((ROOT/ROSTER).read_bytes())
 def tapes(self,days=24):
  tapes=[];absolute=0;rng=np.random.default_rng(528)
  for d in range(days):
   n=1001 if d<days-2 else 9007;base=int(np.datetime64((date(2026,5,23)+timedelta(days=d)).isoformat()+'T00:00:00','ns').astype(np.int64));i=np.arange(n,dtype=np.int64);px=np.resize(np.array([100,101,102,103,104,105,104,103,102,101]),n);vol=np.ones(n)*10
   if d>=days-2:vol[px>=104]=rng.integers(100,800,np.sum(px>=104))
   # Same-ns cohorts, nondivisible session sizes and global sequence.
   ts=base+(i//3)*300000000;t=TickSeries(ts,px,vol,px-1,px,i+absolute,.25,instrument='SYN',contract='SYN');tapes.append(t);absolute+=n
  out=[];first=0
  for k,t in enumerate(tapes):
   following=Clock(int(tapes[k+1].ts_ns[0]),int(tapes[k+1].sequence[0])) if k+1<len(tapes) else None;out.append(SessionTape(t,first,following,int(B.session_ids(t.ts_ns)[0])));first+=len(t)
  return out
 def measured(self,collector,t):
  for i in range(800,len(t)-100,83):
   row={'timestamp_ns':int(t.ts_ns[i]),'sequence':int(t.sequence[i]),'windows':{'20':{'pressure_ratio':1.2,'trade_count_ratio':.8,'directed_progress_ticks':1.,'direction_from_prior':-1 if i%2 else 1}}};collector(row,i,4)
 def test_all_nine_native_counts_and18pair_arrays_exact_with_history_residuals(self):
  outputs=[];scenes=[];diagnostics=[]
  for streaming in (False,True):
   scene=StreamingScene(self.roster,self.plan) if streaming else CrossFamilyScene(self.roster,self.plan,semantic_capture_only=True);selected=[];diags=[]
   for j,st in enumerate(self.tapes()):
    d=np.datetime64(st.session_id*86400,'s').astype(str)[:10];keep=j>=22;events,diag=scene.session(st,d,retain=keep)
    if keep:
     c=CrossFamilyCollector(st,d,events,self.roster,self.plan);self.measured(c,st.ticks)
     if streaming:events.finish()
     z,meta=c.finish(c.n);selected.append(z.copy());diags.append(diag)
   eof=scene.finish();outputs.append(selected);diagnostics.append((diags,eof));scenes.append(scene)
  for a,b in zip(*outputs):np.testing.assert_array_equal(a,b)
  for a,b in zip(diagnostics[0][0],diagnostics[1][0]):
   for x,y in zip(a['config_counts'],b['config_counts']):
    for kind in ('BIRTH','REMOVE','TOUCH','CLASSIFY','unobservable_eof','outside_current_availability'):self.assertEqual(x.get(kind,0),y.get(kind,0))
   self.assertFalse(b['whole_session_event_store']);self.assertLessEqual(b['peak_pending_mutation_records'],self.plan['max_pending_mutation_records'])
  self.assertEqual(diagnostics[0][1],diagnostics[1][1]);self.assertTrue(any(d['config_counts'][0].get('BIRTH',0)>0 for d in diagnostics[1][0]))
  # Same train features and target => exact fixed ridge fits/scores, not NT8 evidence.
  rng=np.random.default_rng(384);training=[]
  for z in outputs[0]:n=len(z);training.append((rng.normal(size=(n,len(FEATURES))),z,rng.integers(0,3,n)))
  a=fit_models(training);b=fit_models([(q[0],z,q[2]) for q,z in zip(training,outputs[1])]);np.testing.assert_array_equal(a[0]['coef'],b[0]['coef'])
  for ma,mb in zip(a[1],b[1]):
   for name in ma:np.testing.assert_array_equal(ma[name]['coef'],mb[name]['coef'])
 def test_total_session_mutations_can_exceed_small_pending_bound_without_loss(self):
  p={**self.plan,'max_pending_mutation_records':100,'max_session_capture_records':100};st=self.tapes(days=2)[-1];# use first contiguous session separately
  st=self.tapes(days=2)[0];scene=StreamingScene(self.roster,p);events,diag=scene.session(st,np.datetime64(st.session_id*86400,'s').astype(str)[:10],retain=True)
  def consume(k,c,records):pass
  for i in range(20,len(st.ticks),17):events.advance(Clock(int(st.ticks.ts_ns[i]),int(st.ticks.sequence[i])),consume)
  events.finish();self.assertGreater(diag['total_causal_mutations_processed'],100);self.assertLessEqual(diag['peak_pending_mutation_records'],100)
 def test_pending_overflow_still_fails_no_prefix_truncation(self):
  p={**self.plan,'max_pending_mutation_records':1};scene=StreamingScene(self.roster,p);st=self.tapes(days=2)[0];events,_=scene.session(st,'2026-05-23',retain=True)
  with self.assertRaises(ValueError):events.advance(Clock(int(st.ticks.ts_ns[-1]),int(st.ticks.sequence[-1])),lambda *args:None)
 def test_must_drain_and_strict_prefix_no_rewind(self):
  scene=StreamingScene(self.roster,self.plan);st=self.tapes(days=2)[0];events,_=scene.session(st,'2026-05-23',retain=True);c=Clock(int(st.ticks.ts_ns[200]),int(st.ticks.sequence[200]));events.advance(c,lambda *args:None)
  with self.assertRaises(ValueError):events.advance(c,lambda *args:None)
  with self.assertRaises(ValueError):scene.session(st,'2026-05-23',retain=True)
  events.finish()
  with self.assertRaises(ValueError):events.finish()
if __name__=='__main__':unittest.main()
