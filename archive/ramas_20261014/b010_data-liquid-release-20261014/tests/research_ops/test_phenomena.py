import unittest
import numpy as np
from tools.research_ops.confluence.phenomena import ClockMeasurements,RangeIndex,BlockedRangeIndex,HOLDOUT_NS
BASE=1781575200000000000

def tape(n=260):
 ns=BASE+np.arange(n,dtype=np.int64)*500_000_000;seq=np.arange(n,dtype=np.int64)
 bid=np.full(n,100,dtype=np.int64);ask=bid+1;price=np.where(seq%3,ask,bid);v=np.ones(n,dtype=np.int64)
 return [ns,seq,price,v,bid,ask]
def records(x,**kwargs):return list(ClockMeasurements(**kwargs).measure(*x,trade_date='2026-06-16'))

class PhenomenaTests(unittest.TestCase):
 def test_range_index_oracle(self):
  r=np.random.default_rng(12);x=r.integers(-900,900,3000);index=BlockedRangeIndex(x)
  for _ in range(1000):
   l=int(r.integers(len(x)));z=int(r.integers(l+1,len(x)+1));self.assertEqual(index.query(l,z),(int(x[l:z].min()),int(x[l:z].max())))
 def test_clock_windows_prefix_oracle(self):
  x=tape();rs=records(x)
  for row in rs:
   i=int(row['sequence']);t=row['timestamp_ns']
   for w in (5,20,60):
    got=row['windows'][str(w)]['current'];ids=[k for k in range(i+1) if x[0][k]>t-w*10**9]
    self.assertEqual(got['count'],len(ids));self.assertEqual(got['volume'],sum(int(x[3][k]) for k in ids))
    buys=sum(int(x[3][k]) for k in ids if x[2][k]>=x[5][k]);sells=sum(int(x[3][k]) for k in ids if x[2][k]<=x[4][k])
    self.assertEqual(got['signed_volume_proxy'],buys-sells)
 def test_same_ns_prefix_no_future(self):
  x=tape();x[0][121]=x[0][120];a=records(x)
  y=[v.copy() for v in x];y[3][121]=999
  b=records(y);self.assertEqual(next(r for r in a if r['sequence']==120),next(r for r in b if r['sequence']==120))
 def test_append_prefix(self):
  x=tape();a=records([v[:181] for v in x]);b=records(x);self.assertEqual(a,b[:len(a)])
 def test_mirror(self):
  x=tape();a=records(x);y=[v.copy() for v in x];y[2]=400-x[2];y[4]=400-x[5];y[5]=400-x[4];b=records(y)
  for ra,rb in zip(a,b):
   for w in ('5','20','60'):
    aa=ra['windows'][w];bb=rb['windows'][w];self.assertEqual(aa['status'],bb['status']);self.assertEqual(aa['direction_from_prior'],-bb['direction_from_prior'])
    if aa['status']=='MEASURABLE_PAIR':self.assertEqual(aa['directed_progress_ticks'],bb['directed_progress_ticks'])
 def test_unknown_not_default_buy(self):
  x=tape();x[5]=x[4]+2;x[2]=x[4]+1
  for r in records(x):
   c=r['windows']['5']['current'];self.assertEqual(c['unknown_volume'],c['volume']);self.assertEqual(c['signed_volume_proxy'],0)
 def test_invalid_quote(self):
  x=tape();x[5]=x[4].copy()
  self.assertTrue(all(r['windows']['5']['current']['status']!='OBSERVABLE' for r in records(x)))
 def test_gap(self):
  x=tape();x[0][140:]+=10_000_000_000
  self.assertTrue(any(r['windows']['20']['current']['status']=='GAP_UNKNOWN' for r in records(x)))
 def test_holdout_and_date(self):
  x=tape();x[0]=np.arange(len(x[0]))+HOLDOUT_NS
  with self.assertRaises(ValueError):records(x)
  with self.assertRaises(ValueError):list(ClockMeasurements().measure(*tape(),trade_date='2026-10-01'))
 def test_capacity_no_truncation(self):
  with self.assertRaises(ValueError):records(tape(),max_anchors=1)
  with self.assertRaises(ValueError):records(tape(),max_ticks=1)
 def test_order(self):
  x=tape();x[1][5]=x[1][4]
  with self.assertRaises(ValueError):records(x)
 def test_zero_volume(self):
  x=tape();x[3][:]=0
  self.assertTrue(any(r['windows']['5']['current']['status']=='ZERO_VOLUME' for r in records(x)))
 def test_half_tick_midpoint(self):
  r=next(x for x in records(tape()) if x['windows']['5']['current']['status']=='OBSERVABLE')
  self.assertEqual(r['windows']['5']['current']['range_midpoint_ticks'],0)
 def test_count_crossfoot(self):
  m=ClockMeasurements();r=list(m.measure(*tape(),trade_date='2026-06-16'))
  for counts in m.summary['windows'].values():self.assertEqual(sum(counts.values()),len(r))
  self.assertFalse(m.summary['outcomes_enabled']);self.assertFalse(m.summary['classifier_states_enabled'])

class PhenomenaRunnerTests(unittest.TestCase):
 def test_kaggle_host_required(self):
  import os
  from unittest.mock import patch
  from tools.research_ops.confluence.phenomena_pilot import run
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(ValueError):run('not-opened',{},'/tmp/not-created')
 def test_output_root_rejected(self):
  import os
  from unittest.mock import patch
  from tools.research_ops.confluence.phenomena_pilot import run
  with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST'}):
   with self.assertRaises(ValueError):run('not-opened',{},'/kaggle/working/private')
 def test_runner_synthetic_receipt(self):
  import os,json,tempfile
  from pathlib import Path
  from types import SimpleNamespace
  from unittest.mock import patch
  from tools.research_ops.confluence.phenomena_pilot import run
  from edgelab.bridge import bars as B
  x=tape();ticks=SimpleNamespace(ts_ns=x[0],sequence=x[1],price_ticks=x[2],volume=x[3],bid_ticks=x[4],ask_ticks=x[5])
  st=SimpleNamespace(ticks=ticks,session_id=int(B.session_ids(x[0])[0]))
  plan=json.loads((Path(__file__).resolve().parents[2]/'docs/research/ops/MNQ_PHENOMENA_P0_PLAN.json').read_bytes())
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST'}),patch('tools.research_ops.confluence.phenomena_pilot.iter_sessions',return_value=iter([st])):
   receipt=run('INVENTED_NOT_READ',plan,Path(d)/'private')
   self.assertEqual(receipt['target_session'],'2026-06-16');self.assertFalse(receipt['outcomes']);self.assertFalse(receipt['state_classification'])
   self.assertTrue((Path(d)/'private/features-private.jsonl').exists());self.assertNotIn('timestamp_ns',receipt)

if __name__=='__main__':unittest.main()
