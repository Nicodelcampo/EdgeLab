import unittest
from tools.research_ops.confluence.phenomena_transitions import StatePath
from tools.research_ops.confluence.asof_intersections import Clock
class TransitionTests(unittest.TestCase):
 def run_path(self,rows):
  p=StatePath();return [p.push(Clock(ns+1,seq),day,s) for ns,seq,day,s in rows]
 def test_prefix_exact_same_ns_and_no_final_duration(self):
  rows=[(0,0,'2026-09-17','A_ONLY'),(5000000000,1,'2026-09-17','A_ONLY'),(5000000000,2,'2026-09-17','E_ONLY'),(10000000000,3,'2026-09-17','E_ONLY')];a=self.run_path(rows);self.assertEqual(a[:3],self.run_path(rows[:3]));self.assertTrue(a[2]['A_TO_E_observed_within_cap']);self.assertEqual(a[1]['duration_seconds'],5);self.assertEqual(a[2]['duration_seconds'],0)
 def test_unknown_gap_and_session_break_no_invented_transition(self):
  for tail in [(5000000000,1,'2026-09-17','UNKNOWN'),(11000000000,1,'2026-09-17','E_ONLY'),(5000000000,1,'2026-09-18','E_ONLY')]:
   a=self.run_path([(0,0,'2026-09-17','A_ONLY'),tail,(tail[0]+5000000000,2,tail[2],'E_ONLY')]);self.assertFalse(a[-1]['A_TO_E_observed_within_cap'])
 def test_rewind_and_expiry(self):
  p=StatePath();p.push(Clock(1,0),'2026-09-17','A_ONLY')
  with self.assertRaises(ValueError):p.push(Clock(1,0),'2026-09-17','E_ONLY')
  p.push(Clock(5000000000,1),'2026-09-17','E_ONLY')
  for i in range(2,28):last=p.push(Clock(i*5000000000,i),'2026-09-17','E_ONLY')
  self.assertFalse(last['A_TO_E_observed_within_cap']);self.assertEqual(last['duration_seconds'],120)
