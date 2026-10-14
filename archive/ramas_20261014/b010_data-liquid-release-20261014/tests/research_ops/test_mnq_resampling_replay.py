import unittest
import numpy as np
from tools.research_ops.benchmarks.mnq_resampling_replay import PLAN, compute, plan_hash, run
class ReplayTests(unittest.TestCase):
 def test_fixed_plan_no_winner_selection(self):
  self.assertEqual(PLAN['cells'],len(PLAN['landmarks'])*len(PLAN['visits'])*len(PLAN['speed'])*len(PLAN['gaps']))
  self.assertFalse(PLAN['scientific_trial']);self.assertFalse(PLAN['adoption_authorized']);self.assertEqual(len(plan_hash()),64)
 def test_exact_counts_and_bands(self):
  rng=np.random.default_rng(100);ix=rng.integers(0,7,size=(10000,7));d=rng.integers(0,50,size=(6,7,3),dtype=np.int64);d[0]=0
  self.assertEqual(compute(d,ix,'baseline'),compute(d,ix,'candidate'))
 def test_empty_support_parity(self):
  d=np.zeros((2,5,3),np.int64);d[:,:,2]=100;ix=np.zeros((100,5),np.int64)
  self.assertEqual(compute(d,ix,'baseline'),compute(d,ix,'candidate'))
 def test_invalid_method(self):
  with self.assertRaises(ValueError):compute(np.zeros((1,2,3),np.int64),np.zeros((4,2),np.int64),'other')
 def test_kaggle_only(self):
  import os
  from unittest.mock import patch
  with patch.dict(os.environ,{},clear=True),self.assertRaisesRegex(ValueError,'Kaggle'):run('not_read','not_read','not_written')
