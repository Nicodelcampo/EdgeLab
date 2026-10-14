import random,unittest
from tools.research_ops.confluence.first_passage import FirstPassage
from tools.research_ops.confluence.asof_intersections import Clock

def point(l,i,p,ns=None,session='2026-09-01'):return l.observe(Clock(ns if ns is not None else i+1,i),2*p,index=i,trade_date=session)
class PassageTests(unittest.TestCase):
    def test_first_observation_after_anchor_not_ohlc_fill(self):
        l=FirstPassage(distance_ticks=2,horizon_ticks=5,max_gap_ns=None);point(l,0,100);l.register('a');self.assertEqual(point(l,1,101),());r=point(l,2,103)[0];self.assertEqual(r.status,'UP_FIRST');self.assertEqual(r.future_observations,2)
    def test_cross_on_horizon_tick_wins_over_no_passage(self):
        l=FirstPassage(distance_ticks=2,horizon_ticks=2,max_gap_ns=None);point(l,0,100);l.register('a');point(l,1,100);self.assertEqual(point(l,2,98)[0].status,'DOWN_FIRST')
    def test_complete_horizon_neither_is_distinct_from_censor(self):
        l=FirstPassage(distance_ticks=2,horizon_ticks=2,max_gap_ns=None);point(l,0,100);l.register('a');point(l,1,100);r=point(l,2,100)[0];self.assertEqual(r.status,'HORIZON_NO_PASSAGE');self.assertTrue(r.usable_response)
        l.register('b');r=l.finish()[0];self.assertEqual(r.status,'EOF_CENSORED');self.assertFalse(r.usable_response)
    def test_gap_censor_precedes_apparent_crossing(self):
        l=FirstPassage(distance_ticks=2,horizon_ticks=5,max_gap_ns=10);point(l,0,100,ns=1);l.register('a');r=point(l,1,110,ns=12)[0];self.assertEqual(r.status,'GAP_CENSORED');self.assertFalse(r.usable_response)
    def test_same_ns_sequence_and_session_censor(self):
        l=FirstPassage(distance_ticks=2,horizon_ticks=5,max_gap_ns=None);point(l,0,100,ns=1);l.register('a');self.assertEqual(point(l,1,103,ns=1)[0].status,'UP_FIRST');l.register('b');self.assertEqual(point(l,2,90,ns=2,session='2026-09-02')[0].status,'SESSION_CENSORED')
    def test_heap_matches_naive_observed_point_oracle(self):
        for seed in range(10):
            rng=random.Random(seed);d=seed+1;h=13;l=FirstPassage(distance_ticks=d,horizon_ticks=h,max_gap_ns=None);pending={};actual={};expected={};p=100
            for i in range(300):
                p+=rng.randint(-4,4)
                for id,(origin,ref) in list(pending.items()):
                    status='UP_FIRST' if p>=ref+d else ('DOWN_FIRST' if p<=ref-d else ('HORIZON_NO_PASSAGE' if i-origin>=h else None))
                    if status:expected[id]=(status,i);del pending[id]
                for row in point(l,i,p):actual[row.anchor_id]=(row.status,row.resolved_index)
                if rng.random()<.3:
                    id=str(i);l.register(id);pending[id]=(i,p)
            self.assertEqual(actual,expected)
            self.assertTrue(all(x.status=='EOF_CENSORED' for x in l.finish()))
    def test_budget_and_reserved_scope_fail_without_partial_labels(self):
        l=FirstPassage(distance_ticks=2,horizon_ticks=2,max_gap_ns=None,max_pending=1);point(l,0,100);l.register('a')
        with self.assertRaises(ValueError):l.register('b')
        with self.assertRaises(ValueError):point(l,1,100,session='2026-10-01')
        self.assertEqual(len(l.active),1)
if __name__=='__main__':unittest.main()
