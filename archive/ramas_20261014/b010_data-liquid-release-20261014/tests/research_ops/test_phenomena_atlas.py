import unittest,json,tempfile,copy
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence.phenomena import ClockMeasurements
from tools.research_ops.confluence.phenomena_atlas import AtlasAggregate,reason,quantiles,run,validate_plan,DATES
from tools.research_ops.confluence.package_phenomena_atlas import build_request,PLAN
from tests.research_ops.test_phenomena import tape
from edgelab.bridge import bars as B
ROOT=Path(__file__).resolve().parents[2]
def plan():return json.loads((ROOT/PLAN).read_bytes())
def rows():return list(ClockMeasurements().measure(*tape(1500),trade_date='2026-06-16'))
class AtlasTests(unittest.TestCase):
 def test_exact_p0_pair_status_denominators(self):
  rs=rows();a=AtlasAggregate(minimum=1)
  for r in rs:a.add(r)
  got=a.finish()
  for w,v in got.items():
   self.assertEqual(v['status_counts'],dict(Counter(r['windows'][w]['status'] for r in rs)))
   self.assertEqual(sum(v['exclusive_reason_counts'].values()),len(rs));self.assertEqual(sum(map(sum,v['pressure_progress_cell_counts'])),v['measurable_pair_denominator'])
   vals=[r['windows'][w]['pressure_ratio'] for r in rs if r['windows'][w]['status']=='MEASURABLE_PAIR']
   self.assertEqual(v['measurable_metrics']['pressure_ratio']['count'],len(vals))
   self.assertEqual(v['measurable_metrics']['pressure_ratio']['quantiles']['0.5'],float(np.median(vals)))
 def test_exclusive_cause_precedence_preserves_joint(self):
  p={'current':{'status':'GAP_UNKNOWN'},'prior':{'status':'QUOTE_UNKNOWN'},'direction_from_prior':0,'status':'UNKNOWN_PAIR'}
  self.assertEqual(reason(p),'CURRENT_GAP_UNKNOWN');p['current']['status']='OBSERVABLE';self.assertEqual(reason(p),'PRIOR_QUOTE_UNKNOWN');p['prior']['status']='OBSERVABLE';self.assertEqual(reason(p),'PRIOR_ZERO_SIGNED_FLOW')
 def test_closed_reason_and_pair_mismatch(self):
  r=rows()[-1]['windows']['5'];r['current']['status']='FREE_FORM_PRIVATE_VALUE'
  with self.assertRaises(ValueError):reason(r)
  r=rows()[-1]['windows']['5'];r['status']='UNKNOWN_PAIR'
  with self.assertRaises(ValueError):reason(r)
 def test_suppression_and_no_extrema(self):
  q=quantiles([1,2,3],100);self.assertIsNone(q['quantiles']);self.assertNotIn('min',q)
  q=quantiles(range(100),100);self.assertEqual(q['quantiles']['0.5'],49.5)
  with self.assertRaises(ValueError):quantiles([float('nan')],100)
 def test_nonfinite_measurable_rejected(self):
  r=rows()[-1];r['windows']['5']['pressure_ratio']=float('inf')
  with self.assertRaises(ValueError):AtlasAggregate().add(r)
 def test_aggregate_capacity_no_truncation(self):
  a=AtlasAggregate(max_anchors=1);r=rows()[0];a.add(r)
  with self.assertRaises(ValueError):a.add(r)
 def test_grid_edges_right_assignment(self):
  r=rows()[-1]
  for p in r['windows'].values():p['pressure_ratio']=1.;p['directed_progress_ticks']=0.
  a=AtlasAggregate();a.add(r);got=a.finish()
  for v in got.values():self.assertEqual(v['pressure_progress_cell_counts'][3][3],1)
 def test_no_market_rows_exported(self):
  a=AtlasAggregate()
  for r in rows():a.add(r)
  text=json.dumps(a.finish(),allow_nan=False)
  for key in ('timestamp_ns','sequence','bid_ticks','ask_ticks','trade_date'):self.assertNotIn(key,text)
 def test_fixed_plan_outcomes_and_gates_rejected(self):
  validate_plan(plan())
  for k,v in [('outcomes',True),('max_gap_ns',3000000000),('minimum_quote_volume_coverage',.6),('max_total_ticks',9000000),('cpu_seconds',900.),('quantiles',[.5]),('target_sessions',list(reversed(DATES)))]:
   p=plan();p[k]=v
   with self.assertRaises(ValueError):validate_plan(p)
  p=plan();p['session_ranges'][0]['start_ns']+=1
  with self.assertRaises(ValueError):validate_plan(p)
 def test_package_compile_and_no_signed_url_in_receipt(self):
  url='https://storage.googleapis.com/kagglesdsdata/datasets/SYNTHETIC/MNQ/MNQ_09-26_ticks_ext.parquet?TEST_ONLY'
  request,r=build_request(ROOT,url=url,source_commit='a'*40);q=request['request'];compile(q['text'],'atlas','exec')
  self.assertTrue(q['isPrivate']);self.assertFalse(q['enableGpu']);self.assertNotIn(url,json.dumps(r));self.assertIn('confluence.phenomena_atlas',q['text']);self.assertIn('/phenomena-atlas',q['text']);self.assertIn('atlas-receipt.json',q['text']);self.assertNotIn('confluence.phenomena_pilot',q['text'])
  with self.assertRaises(ValueError):build_request(ROOT,url=url.replace('storage.googleapis.com','evil.test'),source_commit='a'*40)
 def test_runner_three_synthetic_sessions(self):
  p=plan();sts=[]
  for r in p['session_ranges']:
   x=tape(1500);x[0]=r['start_ns']+1000000000+np.arange(1500,dtype=np.int64)*500000000
   t=SimpleNamespace(ts_ns=x[0],sequence=x[1],price_ticks=x[2],volume=x[3],bid_ticks=x[4],ask_ticks=x[5]);sts.append(SimpleNamespace(ticks=t,session_id=int(B.session_ids(x[0])[0])))
  with tempfile.TemporaryDirectory() as d,patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST'}),patch('tools.research_ops.confluence.phenomena_atlas.iter_sessions',side_effect=[iter([st]) for st in sts]):
   receipt=run('INVENTED_NOT_READ',p,Path(d)/'private');self.assertEqual(receipt['session_count'],3);self.assertEqual(receipt['total_ticks'],4500);self.assertFalse(receipt['outcomes']);self.assertFalse(receipt['private_rows_persisted']);self.assertFalse((Path(d)/'private').exists());self.assertEqual([r['trade_date'] for r in receipt['sessions']],list(DATES))
 def test_runner_missing_session_and_wrong_identity_fail(self):
  with tempfile.TemporaryDirectory() as d,patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST'}),patch('tools.research_ops.confluence.phenomena_atlas.iter_sessions',return_value=iter([])):
   with self.assertRaises(ValueError):run('INVENTED_NOT_READ',plan(),Path(d)/'private')
 def test_runner_outside_kaggle_and_private_output_rejected(self):
  with patch.dict('os.environ',{},clear=True):
   with self.assertRaises(ValueError):run('NOT_READ',plan(),'/tmp/not-created')
  with patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST'}):
   with self.assertRaises(ValueError):run('NOT_READ',plan(),'/kaggle/working/private')
if __name__=='__main__':unittest.main()
