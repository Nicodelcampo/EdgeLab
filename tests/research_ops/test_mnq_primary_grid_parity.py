import unittest,math
import numpy as np,pandas as pd
from tools.research_ops.benchmarks.mnq_primary_grid_parity import PLAN,form_cells,metrics,check_row,same_float,KEYS
from tools.research_ops.session_resampling import multiplicities
class FullGridTests(unittest.TestCase):
 def test_prespecified_census(self):
  n=1
  for k in ['origins','landmarks','dedups','endpoints','visit_definitions','visits','speeds','gaps']:n*=len(PLAN[k])
  self.assertEqual(n,11340);self.assertFalse(PLAN['adoption_authorized'])
 def test_exact_floats(self):
  self.assertTrue(same_float(math.nan,''));self.assertTrue(same_float(2.,'2.0'));self.assertFalse(same_float(1.,str(np.nextafter(1.,2.))))
 def test_metrics_literal_frozen(self):
  d=np.array([[1,2,4],[2,1,5],[0,0,0]]);ix=np.array([[0,1,1],[2,2,2],[0,0,2]])
  v=metrics(d,multiplicities(ix,3));bw=d[ix,0].sum(axis=1);bn=d[ix,:2].sum(axis=(1,2));ok=bn>0;ci=np.quantile(100*bw[ok]/bn[ok],[.025,.975]);self.assertEqual(v['day_lower'],ci[0]);self.assertEqual(v['day_upper'],ci[1]);self.assertEqual(v['signals'],9)
 def test_unknown_session_rejected(self):
  t=pd.DataFrame({'session':['wrong']})
  with self.assertRaises(ValueError):next(form_cells(t,{'event_dates':['day']}))
 def test_all_cells_and_empty_retained(self):
  t=pd.DataFrame(dict(session=['a','a','b'],status=['TARGET_FIRST','OPPOSITE_FIRST','CENSORED'],dedup75=[1,1,0],dedup50=[1,0,1],origin=['real']*3,landmark=[2000]*3,endpoint=[0]*3,visits1=[0,1,5],visits5=[0,0,2],visits_clock10s=[0,1,4],speed_ratio=[1,.5,np.nan],prior_gap_count=[0,0,1]))
  cells=list(form_cells(t,{'event_dates':['a','b','c']}));self.assertEqual(len(cells),11340);self.assertEqual(len({k for k,d in cells}),11340)
  key=('MNQ_09-26','all','real',2000,0,'visits1','all','all','observed');d=dict(cells)[key];np.testing.assert_array_equal(d,[[1,1,2],[0,0,1],[0,0,0]])
 def test_wrong_reference_rejected(self):
  key=('MNQ_09-26','all','real',0,0,'visits1','all','all','observed');v=metrics(np.zeros((2,3),np.int64),multiplicities(np.zeros((1,2),np.int64),2));ref={**dict(zip(KEYS,key)),**{k:('' if isinstance(a,float) and math.isnan(a) else str(a)) for k,a in v.items()}};check_row(key,v,ref);ref['signals']='1'
  with self.assertRaises(ValueError):check_row(key,v,ref)
