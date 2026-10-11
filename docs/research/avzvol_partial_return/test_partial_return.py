import unittest,random
from partial_return import Trade,Zone,Rule,evaluate

def tape(prices,sessions=None,bars=None,aggressors=None):
    return [Trade(i,i*1_000_000_000,bars[i] if bars else i,p,sessions[i] if sessions else 'S',1,aggressors[i] if aggressors else 0) for i,p in enumerate(prices)]

class PartialReturnTests(unittest.TestCase):
    def run_case(self,prices,rule=Rule(20,.5),**kwargs):return evaluate(tape(prices,**kwargs),Zone('Z',90,100,0),rule)
    def test_touch_target(self):
        r=self.run_case([95,105,120,115,110,105,100]);self.assertEqual(r['status'],'TARGET_FIRST');self.assertEqual((r['trigger_seq'],r['frozen_target'],r['frozen_opposite']),(4,100,120))
    def test_equal_opposite(self):self.assertEqual(self.run_case([95,105,120,110,121])['status'],'OPPOSITE_FIRST')
    def test_touch_not_cross(self):
        p=[95,105,120,110,100,105];self.assertEqual(self.run_case(p)['status'],'TARGET_FIRST');self.assertEqual(self.run_case(p,Rule(20,.5,'cross_one_tick'))['status'],'UNRESOLVED_TAPE_END')
    def test_enter_and_cross_mirror_barriers(self):
        p=[95,105,120,110,89];r=self.run_case(p,Rule(20,.5,'cross_one_tick'));self.assertEqual((r['frozen_target'],r['frozen_opposite']),(89,131));self.assertEqual(r['status'],'TARGET_FIRST')
        r=self.run_case(p,Rule(20,.5,'enter_one_tick'));self.assertEqual((r['frozen_target'],r['frozen_opposite']),(99,121))
    def test_no_final_peak_leakage(self):
        r=self.run_case([95,105,120,110,200]);self.assertEqual(r['features']['peak_distance_ticks'],20);self.assertEqual(r['trigger_seq'],3)
    def test_overshoot_not_free_win(self):self.assertEqual(self.run_case([95,105,120,99])['status'],'TOUCH_BEFORE_OBSERVED_TRIGGER')
    def test_session_censoring(self):self.assertEqual(self.run_case([95,105,120,110,100],sessions=['S','S','S','S','T'])['status'],'UNRESOLVED_SESSION_END')
    def test_horizon(self):self.assertEqual(self.run_case([95,105,120,110,100],Rule(20,.5,horizon_bars=1),bars=[0,1,2,3,5])['status'],'UNRESOLVED_HORIZON')
    def test_unknown_imbalance_not_zero(self):
        r=self.run_case([95,105,120,110,100]);self.assertIsNone(r['features']['returning']['delta_over_total_away']);self.assertEqual(r['features']['returning']['known_volume_fraction'],0)
    def test_flow_legs_do_not_double_count_peak(self):
        r=self.run_case([95,105,120,110,100],aggressors=[1,1,1,-1,-1]);self.assertEqual(r['features']['outgoing']['volume'],2);self.assertEqual(r['features']['returning']['volume'],1);self.assertEqual(r['features']['returning']['delta_over_total_away'],-1)
    def test_samebar_velocity(self):
        r=self.run_case([95,105,120,110,100],bars=[0,0,0,0,0]);self.assertEqual(r['features']['returning']['inclusive_bars'],1)
    def test_exact_threshold_and_no_trigger(self):
        self.assertTrue(self.run_case([95,105,120,110,100])['signal']);self.assertFalse(self.run_case([95,105,119,110,100])['signal'])
    def test_outside_anchor_not_eligible(self):self.assertEqual(self.run_case([105,120,110,100])['status'],'ANCHOR_OUTSIDE')
    def test_reject_wrong_order(self):
        ts=tape([95,120,110]);ts[2]=Trade(1,2_000_000_000,2,110,'S');self.assertRaises(ValueError,evaluate,ts,Zone('Z',90,100,0),Rule(20,.5))
    def test_future_features_and_barriers_invariant(self):
        r=self.run_case([95,105,120,110]);k=['trigger_seq','features','frozen_target','frozen_opposite']
        for tail in ([100],[120],[105,200],[109,108,100]):
            s=self.run_case([95,105,120,110]+tail)
            for key in k:self.assertEqual(r[key],s[key])
    def test_random_price_mirroring(self):
        random.seed(731)
        for n in range(300):
            ps=[95,105,120,110]+[random.randrange(80,141) for _ in range(12)]
            for endpoint in ('touch','enter_one_tick','cross_one_tick'):
                r=self.run_case(ps,Rule(20,.5,endpoint));mirror=[190-p for p in ps];q=evaluate(tape(mirror),Zone('M',90,100,0),Rule(20,.5,endpoint))
                with self.subTest(n=n,endpoint=endpoint):
                    self.assertEqual(r['status'],q['status']);self.assertEqual(r['symmetric_distance_ticks'],q['symmetric_distance_ticks']);self.assertEqual(r['trigger_seq'],q['trigger_seq']);self.assertEqual(r['frozen_target'],190-q['frozen_target']);self.assertEqual(r['frozen_opposite'],190-q['frozen_opposite'])
    def test_all_fractions_causal(self):
        for q in (.1,.25,1/3,.5,2/3,.75,.9):
            r=self.run_case([95,105,120,119,118,117,116,115,114,113,112,111,110,109,108,107,106,105,104,103,102,101,100],Rule(20,q))
            with self.subTest(q=q):self.assertTrue(r['signal']);self.assertGreaterEqual(r['features']['actual_retraced_fraction']+1e-12,q);self.assertEqual(r['status'],'TARGET_FIRST')

if __name__=='__main__':unittest.main(verbosity=2)
