import unittest
import numpy as np
from tools.research_ops.session_resampling import multiplicities,resampled_counts

class ExactResamplingTests(unittest.TestCase):
 def test_exact_many_seeds(self):
  for seed in range(8):
   rng=np.random.default_rng(seed);ix=rng.integers(0,13,(250,13));d=rng.integers(0,1000,(13,3),dtype=np.int64)
   self.assertTrue(np.array_equal(resampled_counts(multiplicities(ix,13),d),d[ix].sum(axis=1)))
 def test_same_bootstrap_percent_quantiles(self):
  rng=np.random.default_rng(17331);ix=rng.integers(0,57,(10000,57));d=rng.integers(0,40,(57,3),dtype=np.int64)
  a=d[ix].sum(axis=1);b=resampled_counts(multiplicities(ix,57),d)
  self.assertTrue(np.array_equal(a,b));self.assertTrue(np.array_equal(np.quantile(100*a[:,0]/a[:,:2].sum(axis=1),[.025,.975]),np.quantile(100*b[:,0]/b[:,:2].sum(axis=1),[.025,.975])))
 def test_missing_zero_sessions_retained(self):
  ix=np.array([[0,0,1],[2,2,2]]);d=np.array([[0,0,0],[1,2,3],[0,0,0]])
  self.assertTrue(np.array_equal(resampled_counts(multiplicities(ix,3),d),d[ix].sum(axis=1)))
 def test_rng_not_consumed(self):
  rng=np.random.default_rng(3);ix=rng.integers(0,4,(3,4));state=str(rng.bit_generator.state);multiplicities(ix,4);self.assertEqual(state,str(rng.bit_generator.state))
 def test_bad_indices(self):
  for ix in [np.array([[0,2]]),np.array([[-1,1]]),np.array([[0.,1.]]),np.zeros((2,3),dtype=int)]:
   with self.assertRaises(ValueError):multiplicities(ix,2)
 def test_bounded_draws(self):
  with self.assertRaises(ValueError):multiplicities(np.zeros((20001,1),dtype=int),1)
 def test_bad_weights(self):
  for w in [np.array([[1,0]]),np.array([[3,-1]]),np.array([[1.,1.]])]:
   with self.assertRaises(ValueError):resampled_counts(w,np.ones((2,3),dtype=int))
 def test_overflow_rejected(self):
  with self.assertRaises(ValueError):resampled_counts(np.array([[1,1]]),np.array([[np.iinfo(np.uint64).max],[1]],dtype=np.uint64))
 def test_nonnegative_counts(self):
  with self.assertRaises(ValueError):resampled_counts(np.array([[1,1]]),np.array([[-1],[0]]))
