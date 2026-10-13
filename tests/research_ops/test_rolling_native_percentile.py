import unittest,math
import numpy as np
from edgelab.bridge.indicators.bigtrap2absorption import _percentile
from tools.research_ops.confluence.rolling_native_percentile import RollingNativePercentile
class RollingTests(unittest.TestCase):
 def test_native_float_bits_all_thresholds_duplicate_and_signed_zero_eviction(self):
  rng=np.random.default_rng(731);vals=[0.,-0.,1.,1.,-0.,0.]+list(rng.normal(size=1300))
  for length in (1,2,50,500):
   c=RollingNativePercentile(length);ring=[]
   for v in vals:
    if len(ring)==length:ring.pop(0)
    ring.append(v);c.append(v)
    for q in (0,10,50,70,90,100):self.assertEqual(c.percentile(q).hex(),_percentile(ring,q).hex())
 def test_empty_bounds_and_nonfinite_fail_closed(self):
  c=RollingNativePercentile(2);self.assertTrue(math.isnan(c.percentile(50)))
  for x in (float('nan'),float('inf')):
   with self.assertRaises(ValueError):c.append(x)
  with self.assertRaises(ValueError):RollingNativePercentile(0)
