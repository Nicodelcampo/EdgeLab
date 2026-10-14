import unittest
import numpy as np
from tools.research_ops.confluence.multiasset_crossfamily import ArrivalCuts
class ArrivalCutTests(unittest.TestCase):
 def test_fixed17cuts_reconcile_pooled_loss_and_support_not_edge(self):
  z=np.zeros((4,43));z[:,11]=1
  for off in (25,32):z[:,off+1]=1;z[:,off+2:off+5]=1;z[:2,off+6]=-1;z[2:,off+6]=1
  loss={'CONTINUOUS':np.array([.6,.7,.5,.4]),'ARRIVAL':np.array([.5,.6,.4,.3]),'ARRIVAL_CC':np.array([.7,.8,.6,.5])};c=ArrivalCuts()
  for _ in range(6):c.add(0,z,loss)
  r=c.finish({'scenario_min_pooled_anchors':2000,'scenario_min_sessions':6})[0];g=r['INSIDE_BOTH_AND_BOTH_RETURN'];self.assertEqual(g['anchors'],24);self.assertEqual(g['support_sessions'],6);self.assertEqual(g['arrival_improved_sessions'],6);self.assertAlmostEqual(g['mean_brier_pooled']['ARRIVAL'],.45);self.assertFalse(g['support_screen_passed_not_edge']);self.assertLessEqual(len(r),17)
 def test_missing_no_observed_cut_not_fake_zero_loss(self):
  c=ArrivalCuts();c.add(0,np.zeros((4,43)),{k:np.ones(4)*.5 for k in ('CONTINUOUS','ARRIVAL','ARRIVAL_CC')});self.assertEqual(c.finish({'scenario_min_pooled_anchors':2000,'scenario_min_sessions':6})[0],{})
