"""Invented tapes only; native adapters compared, not NT8 parity certification."""
import json,math,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge import bars as B
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey
from tools.research_ops.confluence.detector_capture import Capture,capture_run
from tools.research_ops.confluence.cross_family_context import ExposureIndex,pair_features
from tools.research_ops.confluence.cross_family_collector import CrossFamilyCollector
from tools.research_ops.confluence.cross_family_scene import CrossFamilyScene
from tools.research_ops.confluence.cross_family_design import MODELS,COUNTS,design
from tools.research_ops.confluence.cross_family_pilot import validate_plan,fit_models,score,run,PLAN,ROSTER
from tools.research_ops.confluence.observed_print_index import ObservedPrintIndex
from tools.research_ops.confluence.session_primitives import SessionTape
from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
from tools.research_ops.confluence.phenomena_models import FEATURES,fit,predict
from test_confluence_detector_capture import trap_tape
ROOT=Path(__file__).resolve().parents[2]
BASE=int(np.datetime64('2026-06-15T00:00:00','ns').astype(np.int64))
CONFIG={'indicator':'avolzonepoi2','config_sha256':'a'*64}
def clock(s,seq=None):return Clock(BASE+s*10**9,s if seq is None else seq)
def event(s,lo=8,hi=12,kind='BIRTH',name='z',family='AVZP2',seq=None,side=1):
 return Capture(kind,ZoneKey(family,'a'*64,'b'*64,name),clock(s,seq),s,0,lo,hi,side,())
def tape(px,seconds=None):
 n=len(px);sec=np.arange(n) if seconds is None else np.asarray(seconds)
 return SimpleNamespace(price_ticks=np.asarray(px),ts_ns=BASE+sec*10**9,sequence=np.arange(n),bid_ticks=np.asarray(px)-1,ask_ticks=np.asarray(px)+1)
def obs(idx,t,i,prior=0,prints=None,mid=None):
 return idx.observe(Clock(int(t.ts_ns[i]),int(t.sequence[i])),midpoint2=2*int(t.price_ticks[i]) if mid is None else mid,prior_clock=Clock(int(t.ts_ns[prior]),int(t.sequence[prior])),prior_midpoint2=2*int(t.price_ticks[prior]),prior_print2=2*int(t.price_ticks[prior]),print2=2*int(t.price_ticks[i]),radius_ticks=4,tape=t,anchor_index=i,prior_index=prior,prints=prints or ObservedPrintIndex(t.price_ticks))
class ExposureTests(unittest.TestCase):
 def test_birth_creator_print_excluded_and_observed_return_not_adjacent(self):
  t=tape([5,5,8,5]);idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),True)],midpoint2=10)
  a=obs(idx,t,1);self.assertAlmostEqual(a['arrival'][2],math.log1p(1));self.assertEqual(a['arrival'][4],0)
  b=obs(idx,t,3);self.assertEqual(b['arrival'][4],1);self.assertAlmostEqual(b['arrival'][2],math.log1p(2))
 def test_two_adjacent_prints_are_not_leave_return(self):
  t=tape([8,5,5]);idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),True)],midpoint2=16)
  self.assertEqual(obs(idx,t,2)['arrival'][4],0)
 def test_gapped_jump_is_not_invented_touch(self):
  t=tape([2,2,8]);idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),True)],midpoint2=4)
  a=obs(idx,t,2,prior=1);self.assertEqual(a['arrival'][2],0);self.assertEqual(a['arrival'][5],1)
 def test_age600_inclusive_not_detector_reset(self):
  t=tape([5,5,5],[0,600,601]);idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),True)],midpoint2=10)
  self.assertIsNotNone(obs(idx,t,1)['near']);self.assertIsNone(obs(idx,t,2)['near']);self.assertEqual(idx.counts['measurement_age_end'],1)
  with self.assertRaises(ValueError):idx.apply(clock(602),[(event(602),True)],midpoint2=10)
 def test_future_same_ns_sequence_cannot_leak(self):
  t=tape([5,5,5],[0,1,1]);idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(1,2),[(event(1,seq=2),True)],midpoint2=10)
  with self.assertRaises(ValueError):obs(idx,t,1)
 def test_sameclock_birth_remove_atomic_no_resurrection(self):
  idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),True),(event(0,kind='REMOVE'),True)],midpoint2=10);self.assertFalse(idx.active)
  with self.assertRaises(ValueError):idx.apply(clock(1),[(event(1),True)],midpoint2=10)
  self.assertTrue(idx.poisoned)
 def test_nonprimary_carry_does_not_enter_exposure(self):
  idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),False)],midpoint2=10);self.assertFalse(idx.active)
 def test_mirror_time_width_side_and_native_removal(self):
  c={'indicator':'bigtrap2','config_sha256':'a'*64};idx=ExposureIndex(c,'2026-06-15',mirror=True);e=event(0,lo=2,hi=6,family='BT2')
  idx.apply(clock(0),[(e,True)],midpoint2=10);s=next(iter(idx.active.values()));self.assertEqual((s.lo2,s.hi2,s.side),(14,18,-1));self.assertEqual(s.available,e.clock)
  idx.apply(clock(1),[(event(1,kind='REMOVE',family='BT2'),True)],midpoint2=10);self.assertFalse(idx.active)
 def test_invalid_holdout_age_and_capacity_poison(self):
  with self.assertRaises(ValueError):ExposureIndex(CONFIG,'2026-10-01')
  with self.assertRaises(ValueError):ExposureIndex(CONFIG,'2026-06-15',age_seconds=500)
  idx=ExposureIndex(CONFIG,'2026-06-15',max_active=1,max_seen=2)
  with self.assertRaises(ValueError):idx.apply(clock(0),[(event(0,name='a'),True),(event(0,name='b'),True)],midpoint2=10)
  with self.assertRaises(ValueError):obs(idx,tape([5,5]),1)
 def test_print_budget_failure_poison_prevents_partial_retry(self):
  idx=ExposureIndex(CONFIG,'2026-06-15');idx.apply(clock(0),[(event(0),True)],midpoint2=10);t=tape([5,5]);p=ObservedPrintIndex(t.price_ticks,max_queries=1)
  with self.assertRaises(ValueError):obs(idx,t,1,prints=p)
  self.assertTrue(idx.poisoned)
 def test_random_nearest_and_local_union_against_brute_force(self):
  rng=np.random.default_rng(522)
  for repeat in range(25):
   t=tape(rng.integers(-40,40,size=15));idx=ExposureIndex(CONFIG,'2026-06-15');bands=[]
   for k in range(30):
    lo=int(rng.integers(-70,70));hi=lo+int(rng.integers(0,15));bands.append((lo,hi))
   idx.apply(clock(0),[(event(0,lo,hi,name=str(k)),True) for k,(lo,hi) in enumerate(bands)],midpoint2=0)
   for i in range(1,15):
    r=obs(idx,t,i);mid=2*int(t.price_ticks[i]);domain=set(range(mid-8,mid+9));cells=set().union(*(set(range(lo,hi+1)) for lo,hi in bands));self.assertAlmostEqual(r['density'][2],len(domain&cells)/17)
    def distance(s):return max(s.lo2-mid,mid-s.hi2,0)
    expected=min(idx.active.values(),key=lambda s:(distance(s),s.hi2-s.lo2,s.key));self.assertEqual(r['near'],expected)

class CollectorDesignTests(unittest.TestCase):
 def setUp(self):self.roster=json.loads((ROOT/ROSTER).read_bytes());self.plan=json.loads((ROOT/PLAN).read_bytes())
 def test_immutable_plan_roster_flags(self):
  validate_plan(self.plan,self.roster)
  self.plan['holdout']=True
  with self.assertRaises(ValueError):validate_plan(self.plan,self.roster)
 def test_market_requires_kaggle(self):
  with patch.dict('os.environ',{},clear=True):
   with self.assertRaisesRegex(ValueError,'Kaggle'):run('unused',self.plan,'/tmp/private',{})
 def test_empty_all18pairs_common_population_not_touch_only(self):
  t=tape(np.full(32,5));st=SimpleNamespace(ticks=t);plan={**self.plan,'max_common_anchors_per_session':4};c=CrossFamilyCollector(st,'2026-06-15',[[] for _ in range(9)],self.roster,plan)
  row={'timestamp_ns':BASE+30*10**9,'sequence':30,'windows':{'20':{'pressure_ratio':1.,'trade_count_ratio':1.,'directed_progress_ticks':0.,'direction_from_prior':1}}};c(row,30,4);z,meta=c.finish(1)
  self.assertEqual(z.shape,(1,2,18,43));self.assertTrue(np.all(z==0));self.assertEqual(len(meta['pair_counts']),18);self.assertTrue(all(p['anchors']==1 for p in meta['pair_counts']))
 def test_controls_equal_dimension_finite_not_target_fit(self):
  rng=np.random.default_rng(54);x=rng.normal(size=(100,len(FEATURES)));z=rng.normal(size=(100,2,43))
  for name in MODELS:self.assertEqual(design(x,z,name).shape,(100,COUNTS[name]))
  for a,b in (('GEOMETRY','GEOMETRY_CC'),('ARRIVAL','ARRIVAL_CC'),('INTERACTION','INTERACTION_CC')):self.assertEqual(design(x,z,a).shape,design(x,z,b).shape)
  with self.assertRaises(ValueError):design(x,z[:,:1],'ARRIVAL')
 def test_shared_baseline_training_weighted_per_session(self):
  rng=np.random.default_rng(63);training=[]
  for n in (110,200):training.append((rng.normal(size=(n,len(FEATURES))),rng.normal(size=(n,2,18,43)),rng.integers(0,3,n)))
  continuous,pairs,prior=fit_models(training);x=np.concatenate([q[0] for q in training]);y=np.concatenate([q[2] for q in training]);w=np.concatenate([np.full(len(q[2]),.5/len(q[2])) for q in training]);ref=fit(x,y,w)
  np.testing.assert_array_equal(continuous['coef'],ref['coef']);self.assertEqual(len(pairs),18);np.testing.assert_allclose(prior,.5*np.bincount(training[0][2],minlength=3)/110+.5*np.bincount(training[1][2],minlength=3)/200)
 def test_collector_mirror_uses_availability_quote_not_creator_quote(self):
  t=tape(np.full(32,5));t.bid_ticks[25]=19;t.ask_ticks[25]=21;events=[[] for _ in range(9)];config=self.roster['configs'][0]
  e=Capture('BIRTH',ZoneKey('AVZP2',config['config_sha256'],'b'*64,'zone'),clock(25),24,0,8,12,1,());events[0]=[(e.clock,[(e,True)])]
  c=CrossFamilyCollector(SimpleNamespace(ticks=t),'2026-06-15',events,self.roster,{**self.plan,'max_common_anchors_per_session':2});row={'timestamp_ns':clock(30).ns,'sequence':30,'windows':{'20':{'pressure_ratio':1.,'trade_count_ratio':1.,'directed_progress_ticks':0.,'direction_from_prior':1}}};c(row,30,4)
  s=next(iter(c.indexes[1][0].active.values()));self.assertEqual((s.lo2,s.hi2),(68,72))

class NativeSceneTests(unittest.TestCase):
 def test_nine_profiles_native_events_exact_multisession_and_eof(self):
  roster=json.loads((ROOT/ROSTER).read_bytes());plan=json.loads((ROOT/PLAN).read_bytes());t=trap_tape(5051,True);t.ts_ns[2507:]+=86400*10**9
  ids=B.session_ids(t.ts_ns);edges=[0,2507,len(t)];scene=CrossFamilyScene(roster,plan);got=[[] for _ in range(9)];unavailable=[0]*9
  for start,end in zip(edges[:-1],edges[1:]):
   sub=TickSeries(*(getattr(t,k)[start:end] for k in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),t.tick_size);following=Clock(int(t.ts_ns[end]),int(t.sequence[end])) if end<len(t) else None;date=np.datetime64(int(ids[start])*86400,'s').astype(str)[:10]
   groups,diag=scene.session(SessionTape(sub,start,following,int(ids[start])),date,retain=True)
   for k,gg in enumerate(groups):
    got[k].extend(r for _,rs in gg for r,primary in rs);unavailable[k]+=diag['config_counts'][k].get('unobservable_eof',0)
  eof=scene.finish();eofmap={r['config_sha256']:r['unobservable_eof'] for r in eof}
  for k,c in enumerate(roster['configs']):
   if c['indicator']=='bigtrap2absorption':_,ref=capture_run('BT2A',t,params=c['params']);unavailable[k]+=eofmap[c['config_sha256']]
   else:
    size=int(c['bar_spec'].split(':')[1]);bars=B.build_tick_bars(t,size)
    if c['indicator']=='bigtrap2':_,ref=capture_run('BT2',t,bars=bars,footprints=B.build_footprints(t,bars),params=c['params'])
    else:_,ref=capture_run('AVZP2',t,bars=bars,footprints=build_total_footprint_csr_nt8(t,bars),sessions=B.session_ids(bars.end_ns),params=c['params'])
   # Cross-session availability generated by a prior session collector is
   # deliberately outside primary measurement scope, NOT silently backfilled.
   expected=tuple(r for r in ref.records if not (r.consumed_tick_index<2507 and r.clock.sequence>=2507 and c['indicator']!='bigtrap2absorption'))
   self.assertEqual(tuple(got[k]),expected,c['config_sha256']);self.assertEqual(unavailable[k],ref.unavailable_time_events)
if __name__=='__main__':unittest.main()
