from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"tools"))
from gc_pressure_panel import pressure_gate,sign_class,past_baseline


class PressureTests(unittest.TestCase):
    def q(self):
        return dict(category="ZONE",row=10,ts_us=2_000_000,
            l2=dict(gate="PASS",available_row=8,available_ts_us=1_999_000,
                    snapshot_age_us=1_000_000,values=dict(full_window_available=True,
                    directional_queue_imbalance_1=.2,
                    directional_endpoint_ofi_per_touch_depth=-.3)))

    def test_age_boundary_inclusive(self):
        self.assertEqual(pressure_gate(self.q()),"PASS")

    def test_age_over_boundary_excluded(self):
        q=self.q();q["l2"]["snapshot_age_us"]+=1
        self.assertEqual(pressure_gate(q),"STALE_OVER_1000MS")

    def test_same_timestamp_not_prior(self):
        q=self.q();q["l2"]["available_ts_us"]=q["ts_us"]
        self.assertEqual(pressure_gate(q),"NOT_STRICT_PRIOR")

    def test_future_raw_row_not_prior(self):
        q=self.q();q["l2"]["available_row"]=11
        self.assertEqual(pressure_gate(q),"NOT_STRICT_PRIOR")

    def test_incomplete_window_not_zero(self):
        q=self.q();q["l2"]["values"]["full_window_available"]=False
        self.assertEqual(pressure_gate(q),"INCOMPLETE_10S_WINDOW")

    def test_null_feature_not_zero(self):
        q=self.q();q["l2"]["values"]["directional_queue_imbalance_1"]=None
        self.assertEqual(pressure_gate(q),"FEATURE_UNAVAILABLE")

    def test_nonprospective_retained_but_not_eligible(self):
        q=self.q();q["category"]="MIRROR_50";q["geometry"]={"prospective_event_eligible":False}
        self.assertEqual(pressure_gate(q),"NOT_PROSPECTIVE")

    def test_four_signs_and_unknown(self):
        self.assertEqual(sign_class(.2,.3),"BOTH_WITH_DIRECTION")
        self.assertEqual(sign_class(-.2,-.3),"BOTH_AGAINST_DIRECTION")
        self.assertEqual(sign_class(.2,-.3),"DISAGREE")
        self.assertEqual(sign_class(0,.3),"SOME_NEUTRAL")
        self.assertEqual(sign_class(None,.3),"UNKNOWN")

    def test_baseline_excludes_same_time_future_row(self):
        b=past_baseline(np.array([10,12,100]),np.array([1,2,90]),
                        np.array([1,4,9]),np.array([100,200,200]),4,200,-1)
        self.assertEqual(b["reference_trade_tick"],12)
        self.assertEqual(b["directional_move_10s_ticks"],-2)
        self.assertEqual(b["volume_10s"],3)
        self.assertEqual(b["trade_count_10s"],2)


if __name__=="__main__":unittest.main()