import unittest
from tools.research_ops.confluence.arrival import ArrivalObserver,Tick
from tools.research_ops.confluence.episodes import Episode,Event
from tools.research_ops.confluence.asof_intersections import Clock

def ep(c,lo=10,hi=20,id='x',rev=0,born=None):return Episode(id,(),born or c,c,lo,hi,rev)
def tick(i,p,ns=None,side=1):return Tick(Clock(ns or 1000000000*(i+1),i),p,2.,side)
class ArrivalTests(unittest.TestCase):
    def test_birth_inside_not_arrival(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=2);t=tick(0,12);r=a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);self.assertEqual(r[0].kind,'AT_CREATION');self.assertEqual(r[0].encounter_number,0)
    def test_touch_exit_revisit(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=2);t=tick(0,0);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);r=a.observe(tick(1,12));self.assertEqual(r[0].kind,'FIRST_OBSERVED_TOUCH');self.assertEqual(r[0].approach_side,1)
        self.assertEqual(a.observe(tick(2,14)),());self.assertEqual(a.observe(tick(3,24))[0].kind,'OBSERVED_EXIT');r=a.observe(tick(4,18));self.assertEqual(r[0].kind,'REVISIT');self.assertEqual(r[0].encounter_number,2)
    def test_gap_not_invented_touch(self):
        a=ArrivalObserver(trade_date='2026-09-01');t=tick(0,0);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);r=a.observe(tick(1,30));self.assertEqual(r[0].kind,'GAP_THROUGH_NO_INSIDE_PRINT');self.assertEqual(r[0].encounter_number,0)
    def test_moving_band_onto_stationary_price_not_arrival(self):
        a=ArrivalObserver(trade_date='2026-09-01');t=tick(0,0);old=ep(t.clock);a.observe(t,[Event('START',old,t.clock,'new')]);t=tick(1,0);r=a.observe(t,[Event('UPDATE',ep(t.clock,-2,2,rev=1,born=old.recognized),t.clock,'change')]);self.assertEqual(r[0].kind,'AT_GEOMETRY_REVISION')
    def test_removed_band_cannot_touch(self):
        a=ArrivalObserver(trade_date='2026-09-01');t=tick(0,0);e=ep(t.clock);a.observe(t,[Event('START',e,t.clock,'new')]);t=tick(1,12);self.assertEqual(a.observe(t,[Event('END',e,t.clock,'removed')]),())
    def test_features_n_minus_one_rate_and_proxy_flow(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=3);t=tick(0,0);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);a.observe(tick(1,4));r=a.observe(tick(2,12))[0];f=r.features
        self.assertEqual(f.count,3);self.assertEqual(f.rate_per_s,1.);self.assertEqual(f.net_ticks,6.);self.assertEqual(f.path_ticks,6.);self.assertEqual(f.efficiency,1.);self.assertEqual(f.signed_volume_proxy,6.)
    def test_same_ns_sequence_distinct_and_no_infinite_rate(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=2);t=tick(0,0,ns=100);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);r=a.observe(tick(1,12,ns=100))[0];self.assertIsNone(r.features.rate_per_s)
    def test_incomplete_window_unknown_not_zero(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=256);t=tick(0,0);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);f=a.observe(tick(1,12))[0].features;self.assertEqual(f.status,'INCOMPLETE_WINDOW');self.assertIsNone(f.net_ticks)
    def test_unknown_aggressor_no_filled_flow(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=2);t=tick(0,0,side=0);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);f=a.observe(tick(1,12))[0].features;self.assertIsNone(f.signed_volume_proxy)
    def test_capacity_fail_not_truncate(self):
        a=ArrivalObserver(trade_date='2026-09-01',max_candidates=1);t=tick(0,0)
        with self.assertRaises(ValueError):a.observe(t,[Event('START',ep(t.clock,id='x'),t.clock,'new'),Event('START',ep(t.clock,id='y'),t.clock,'new')])
        self.assertTrue(a.poisoned)
    def test_prefix_records_immutable(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=2);t=tick(0,0);a.observe(t,[Event('START',ep(t.clock),t.clock,'new')]);r=a.observe(tick(1,12));a.observe(tick(2,30));self.assertEqual(r[0].features.net_ticks,6.)
    def test_holdout_rejected(self):
        with self.assertRaises(ValueError):ArrivalObserver(trade_date='2026-10-01')
if __name__=='__main__':unittest.main()
