import unittest
import numpy as np
from tools.research_ops.confluence.observed_print_index import ObservedPrintIndex
class PrintIndexTests(unittest.TestCase):
 def test_gap_through_does_not_invent_touch(self):
  p=ObservedPrintIndex(np.array([1,10]));self.assertEqual(p.query(8,12,left=0,right=2)['observed_print_count'],0)
 def test_half_tick_odd_point_and_negative_closed_endpoints(self):
  p=ObservedPrintIndex(np.array([-3,-2,0,1,2]))
  self.assertEqual(p.query(-5,-5,left=0,right=5)['observed_print_count'],0)
  self.assertEqual(p.query(-6,2,left=0,right=5)['observed_print_count'],4)
 def test_future_prints_and_creation_excluded_by_explicit_prefix(self):
  p=ObservedPrintIndex(np.array([5,1,1,5]))
  self.assertEqual(p.query(10,10,left=1,right=3)['observed_print_count'],0)
  r=p.query(10,10,left=1,right=4);self.assertEqual(r['first_observed_index'],3)
 def test_random_exact_counts_and_first_last_against_scan(self):
  rng=np.random.default_rng(939)
  for _ in range(100):
   px=rng.integers(-50,50,size=500,dtype=np.int64);p=ObservedPrintIndex(px)
   for _ in range(100):
    l,r=sorted(map(int,rng.integers(0,501,size=2)));lo,hi=sorted(map(int,rng.integers(-120,120,size=2)))
    idx=np.flatnonzero((2*px[l:r]>=lo)&(2*px[l:r]<=hi))+l;result=p.query(lo,hi,left=l,right=r)
    self.assertEqual(result['observed_print_count'],len(idx));self.assertEqual(result['first_observed_index'],int(idx[0]) if len(idx) else None);self.assertEqual(result['last_observed_index'],int(idx[-1]) if len(idx) else None)
 def test_overflow_poison_no_silent_level_truncation(self):
  p=ObservedPrintIndex(np.arange(20),max_price_levels_per_query=2)
  with self.assertRaises(ValueError):p.query(0,40,left=0,right=20)
  self.assertTrue(p.poisoned)
  with self.assertRaises(ValueError):p.query(0,0,left=0,right=1)
 def test_empty_retrograde_or_bad_tape_rejected(self):
  with self.assertRaises(ValueError):ObservedPrintIndex(np.array([]))
  p=ObservedPrintIndex(np.array([1,2]))
  for kw in [{'left':2,'right':1},{'left':0,'right':3}]:
   with self.assertRaises(ValueError):p.query(0,2,**kw)
if __name__=='__main__':unittest.main()
