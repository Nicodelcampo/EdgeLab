import unittest
from tools.research_ops.admission import ResourceSnapshot,assess_admission
class AdmissionTests(unittest.TestCase):
    def check(self,snapshot):return assess_admission(snapshot,requested_peak_bytes=100,headroom_bytes=50)
    def test_fit_not_authority(self):
        out=self.check(ResourceSnapshot(500,1000,False));self.assertTrue(out['resource_fit']);self.assertIs(out['execution_allowed'],False);self.assertIs(out['reservation_created'],False)
    def test_memory_blocked(self):self.assertFalse(self.check(ResourceSnapshot(900,1000,False))['resource_fit'])
    def test_heavy_overlap_blocked(self):self.assertIn('HEAVY_WORKER_ALREADY_ACTIVE',self.check(ResourceSnapshot(500,1000,True))['reasons'])
    def test_unknown_limit_blocked(self):
        with self.assertRaises(ValueError):self.check(ResourceSnapshot(500,0,False))
    def test_snapshot_booleans(self):
        with self.assertRaises(ValueError):self.check(ResourceSnapshot(True,1000,False))
    def test_peak_booleans(self):
        with self.assertRaises(ValueError):assess_admission(ResourceSnapshot(0,1000,False),requested_peak_bytes=True,headroom_bytes=50)
    def test_no_cache_reclaim_assumption(self):self.assertFalse(self.check(ResourceSnapshot(1000,1000,False))['resource_fit'])
    def test_exact_bound(self):self.assertTrue(self.check(ResourceSnapshot(850,1000,False))['resource_fit'])
