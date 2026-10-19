import unittest,json,copy,tempfile
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence.phenomena_response import SecondsResponse
from tools.research_ops.confluence.phenomena_states import Calibration,classify,cell,DATE_TRAIN,SESSION_BOUNDS
from tools.research_ops.confluence.phenomena_science_pilot import run,validate_plan
from tools.research_ops.confluence.build_target_free_pilot import digest
from tools.research_ops.confluence.phenomena import ClockMeasurements,HOLDOUT_NS
from tests.research_ops.test_phenomena import tape
from edgelab.bridge import bars as B
ROOT=Path(__file__).resolve().parents[2]
BASE=SESSION_BOUNDS['2026-06-15'][0]+10**9
def arrays(times,mid):
 ns=BASE+np.array(times,dtype=np.int64)*10**9;seq=np.arange(len(ns),dtype=np.int64);b=np.array(mid,dtype=np.int64);return ns,seq,b,b+2
def cal():
 c={'schema':'phenomena_state_calibration_v1','training_trade_date':DATE_TRAIN,'minimum_cell_anchors':100,'outcomes_used':False,'cells':{}}
 for k in ('RTH:1','OTHER:1','RTH:-1','OTHER:-1'):c['cells'][k]={'anchors':200,'supported':True,'current_pressure_q80':10.,'current_pressure_q20':2.,'prior_pressure_q80':10.,'stall_abs_progress_max':2.,'stall_range_max':4.,'stall_path_max':8.}
 c['sha256']=digest(c);return c
def row():
 def w(buy,sell):return {'status':'OBSERVABLE','buy_volume':float(buy),'sell_volume':float(sell),'signed_volume_coverage':1.,'range_midpoint_ticks':2.,'path_midpoint_ticks':3.}
 p={'status':'MEASURABLE_PAIR','direction_from_prior':1,'current':w(12,1),'prior':w(30,1),'directed_progress_ticks':1.,'prior_directed_progress_ticks':5.,'pressure_ratio':.4,'trade_count_ratio':.4}
 return {'trade_date':'2026-06-15','timestamp_ns':BASE,'windows':{'20':p}}
def oracle(xs,i,s,d):
 ns,seq,b,a=xs;n=len(ns);deadline=int(ns[i])+60000000000;ref=int(b[i]+a[i])
 if b[i]<=0 or a[i]<=b[i]:return 'ORIGIN_QUOTE_UNKNOWN'
 k=i+1
 while k<n:
  if int(ns[k])-int(ns[k-1])>2000000000:return 'GAP_CENSORED'
  if b[k]<=0 or a[k]<=b[k]:return 'QUOTE_CENSORED'
  if ns[k]<=deadline:
   delta=s*(int(b[k]+a[k])-ref)
   if delta>=2*d:return 'CONTINUATION_FIRST'
   if delta<=-2*d:return 'REVERSAL_FIRST'
  if ns[k]>deadline:return 'HORIZON_NO_OBSERVED_PASSAGE'
  if ns[k]==deadline and (k==n-1 or ns[k+1]>deadline):return 'HORIZON_NO_OBSERVED_PASSAGE'
  k+=1
 return 'EOF_CENSORED'
class SecondsResponseTests(unittest.TestCase):
 def test_random_sequence_oracle(self):
  rng=np.random.default_rng(118)
  for _ in range(100):
   n=110;ns=BASE+np.cumsum(rng.integers(0,3000000001,n,dtype=np.int64));seq=np.arange(n,dtype=np.int64);b=100+np.cumsum(rng.integers(-2,3,n,dtype=np.int64));a=b+rng.integers(1,4,n,dtype=np.int64)
   if rng.random()<.5:a[int(rng.integers(n))]=0
   xs=(ns,seq,b,a);m=SecondsResponse(*xs)
   for i in (0,2,40,109):
    for direction in (-1,1):self.assertEqual(m.label(i,direction=direction,distance_ticks=4)['status'],oracle(xs,i,direction,4))
 def test_final_exact_horizon_passage(self):
  xs=arrays(list(range(61)),[100]*60+[105]);self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'CONTINUATION_FIRST')
 def test_after_horizon_hit_not_counted(self):
  xs=arrays(list(range(62)),[100]*61+[105]);self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'HORIZON_NO_OBSERVED_PASSAGE')
 def test_same_ns_later_sequence_at_deadline(self):
  xs=arrays(list(range(61))+[60],[100]*61+[105]);self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'CONTINUATION_FIRST')
 def test_gap_and_quote_precede_crossing(self):
  xs=arrays([0,3],[100,105]);self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'GAP_CENSORED')
  xs=arrays([0,1],[100,105]);xs[3][1]=0;self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'QUOTE_CENSORED')
 def test_eof_distinct_from_no_passage(self):
  xs=arrays([0,1,2],[100]*3);self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'EOF_CENSORED')
 def test_early_hit_not_retroactively_censored(self):
  xs=arrays([0,1,100],[100,105,100]);self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'CONTINUATION_FIRST')
 def test_halftick_origin_midpoint(self):
  xs=arrays([0,1],[100,104]);xs[3][0]=101;self.assertEqual(SecondsResponse(*xs).label(0,direction=1,distance_ticks=4)['status'],'CONTINUATION_FIRST')
 def test_direction_mirror(self):
  xs=arrays([0,1],[100,105]);self.assertEqual(SecondsResponse(*xs).label(0,direction=-1,distance_ticks=4)['status'],'REVERSAL_FIRST')
 def test_caps_poison_no_truncation(self):
  xs=arrays([0,1,2],[100]*3);m=SecondsResponse(*xs,max_scan_elements=1)
  with self.assertRaises(ValueError):m.label(0,direction=1,distance_ticks=4)
  with self.assertRaises(ValueError):m.label(1,direction=1,distance_ticks=4)
  m=SecondsResponse(*xs,max_anchors=1);m.label(0,direction=1,distance_ticks=4)
  with self.assertRaises(ValueError):m.label(1,direction=1,distance_ticks=4)
 def test_invalid_holdout_order_and_horizon(self):
  xs=arrays([0,1],[100,100]);xs[0][:]=HOLDOUT_NS
  with self.assertRaises(ValueError):SecondsResponse(*xs)
  xs=arrays([1,0],[100,100])
  with self.assertRaises(ValueError):SecondsResponse(*xs)
  xs=arrays([0,1],[100,100])
  with self.assertRaises(ValueError):SecondsResponse(*xs).label(0,direction=1,distance_ticks=0)
  with self.assertRaises(ValueError):SecondsResponse(*xs).label(0,direction=1,distance_ticks=4,horizon_ns=1)
class StateTests(unittest.TestCase):
 def test_both_are_possible_not_mutually_exclusive(self):self.assertEqual(classify(row(),cal())['state'],'BOTH')
 def test_excursion_return_not_absorption(self):
  r=row();r['windows']['20']['current']['path_midpoint_ticks']=100.;x=classify(r,cal());self.assertEqual(x['state'],'E_ONLY');self.assertIn('HIGH_PRESSURE_EXCURSION_RETURN',x['tags'])
 def test_decay_without_prior_impulse_not_exhaustion(self):
  r=row();r['windows']['20']['prior_directed_progress_ticks']=-5.;self.assertEqual(classify(r,cal())['state'],'A_ONLY')
 def test_pressure_decay_alone_not_joint_activity_decay(self):
  r=row();r['windows']['20']['trade_count_ratio']=.8;self.assertEqual(classify(r,cal())['state'],'A_ONLY')
 def test_low_pressure_is_neither_not_absorption(self):
  r=row();r['windows']['20']['current']['buy_volume']=1.;r['windows']['20']['prior_directed_progress_ticks']=0.;self.assertEqual(classify(r,cal())['state'],'NEITHER')
 def test_unknown_coverage_and_calibration(self):
  r=row();r['windows']['20']['current']['signed_volume_coverage']=.7;self.assertEqual(classify(r,cal())['state'],'UNKNOWN')
  c=cal();c['cells']={};c['sha256']=digest({k:v for k,v in c.items() if k!='sha256'});self.assertEqual(classify(row(),c)['reason'],'CALIBRATION_CELL_UNSUPPORTED')
 def test_frozen_hash_chronology_and_spoofed_date(self):
  c=cal();c['cells']['OTHER:1']['anchors']+=1
  with self.assertRaises(ValueError):classify(row(),c)
  r=row();r['trade_date']='2026-06-12'
  with self.assertRaises(ValueError):Calibration().add(r)
  with self.assertRaises(ValueError):classify(r,cal())
 def test_phase_nanosecond_boundary_no_float_rounding(self):
  r=row();t=int(__import__('datetime').datetime.fromisoformat('2026-06-15T13:30:00+00:00').timestamp())*10**9;r['timestamp_ns']=t-1;self.assertEqual(cell(r),'OTHER:1');r['timestamp_ns']=t;self.assertEqual(cell(r),'RTH:1')
 def test_calibration_supported_quantiles(self):
  c=Calibration();r=row();r['trade_date']='2026-06-12';r['timestamp_ns']=SESSION_BOUNDS[DATE_TRAIN][0]+10**9
  for i in range(100):q=copy.deepcopy(r);q['windows']['20']['current']['buy_volume']=float(i+1);c.add(q)
  f=c.freeze();self.assertTrue(f['cells']['OTHER:1']['supported']);self.assertAlmostEqual(f['cells']['OTHER:1']['current_pressure_q80'],80.2);self.assertFalse(f['outcomes_used'])
 def test_nonfinite_components_rejected(self):
  r=row();r['windows']['20']['current']['path_midpoint_ticks']=float('nan')
  with self.assertRaises(ValueError):classify(r,cal())
class ScienceRunnerTests(unittest.TestCase):
 def test_fixed_plan_and_host(self):
  p=json.loads((ROOT/'docs/research/ops/MNQ_PHENOMENA_SCIENCE_PILOT_PLAN.json').read_bytes());validate_plan(p)
  for k,v in [('inference',True),('holdout',True),('max_gap_ns',3000000000),('pressure_high_quantile',.7),('response_horizon_ns',15000000000),('outcomes',False),('fit_models',True)]:
   q=copy.deepcopy(p);q[k]=v
   with self.assertRaises(ValueError):validate_plan(q)
  with patch.dict('os.environ',{},clear=True):
   with self.assertRaises(ValueError):run('NOT_READ',p,'/tmp/not-created')
 def test_three_sessions_synthetic_only_aggregates(self):
  p=json.loads((ROOT/'docs/research/ops/MNQ_PHENOMENA_SCIENCE_PILOT_PLAN.json').read_bytes());sts=[]
  for r in p['session_ranges']:
   x=tape(1600);x[0]=r['start_ns']+10**9+np.arange(1600,dtype=np.int64)*500000000;t=SimpleNamespace(ts_ns=x[0],sequence=x[1],price_ticks=x[2],volume=x[3],bid_ticks=x[4],ask_ticks=x[5]);sts.append(SimpleNamespace(ticks=t,session_id=int(B.session_ids(x[0])[0])))
  with tempfile.TemporaryDirectory() as d,patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST'}),patch('tools.research_ops.confluence.phenomena_science_pilot.iter_sessions',side_effect=[iter([st]) for st in sts]):
   out=run('INVENTED_NOT_READ',p,Path(d)/'private');self.assertEqual(out['total_ticks'],4800);self.assertFalse(out['training_outcomes_used']);self.assertFalse(out['inference']);self.assertFalse(out['private_rows_persisted'])
   for s in out['evaluation_sessions']:self.assertEqual(sum(s['state_counts'].values()),s['anchors']);self.assertEqual(sum(sum(v.values()) for v in s['state_response_counts'].values()),s['anchors'])
   for k in ('timestamp_ns','bid_ticks','ask_ticks','sequence'):self.assertNotIn(k,json.dumps(out))
if __name__=='__main__':unittest.main()
